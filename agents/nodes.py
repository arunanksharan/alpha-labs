"""Individual agent nodes for the LangGraph research pipeline.

Each function takes a ResearchState, performs its step, and returns the
modified state.  Nodes never raise -- they catch exceptions and record
errors so the pipeline can produce partial results.
"""

from __future__ import annotations

import logging

from agents.state import AgentStatus, ResearchState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Research Agent -- data loading, feature computation, signal generation
# ---------------------------------------------------------------------------


def research_agent(state: ResearchState) -> ResearchState:
    """Fetch market data, compute features, and generate signals."""
    state.add_event("research", AgentStatus.RUNNING, "Fetching data...")

    # -- Load prices --------------------------------------------------------
    try:
        from core.adapters import fetch_and_prepare_prices
        from core.serialization import df_to_json

        prices = fetch_and_prepare_prices(
            state.ticker, state.start_date, state.end_date
        )
        state.prices = df_to_json(prices)
    except Exception as exc:
        msg = f"Failed to load price data: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.add_event("research", AgentStatus.FAILED, msg)
        return state

    # -- Resolve strategy & compute features --------------------------------
    state.add_event("research", AgentStatus.RUNNING, "Computing features...")
    try:
        from core.orchestrator import _compute_features, _ensure_strategies_loaded
        from core.strategies import StrategyRegistry

        _ensure_strategies_loaded()
        strategy = StrategyRegistry.get(state.strategy_name)
        features = _compute_features(
            strategy.required_features, prices, state.ticker
        )
        state.features = df_to_json(features)
    except Exception as exc:
        msg = f"Feature computation failed: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.add_event("research", AgentStatus.FAILED, msg)
        return state

    # -- Generate signals ---------------------------------------------------
    try:
        from core.serialization import signal_to_json

        signals = strategy.generate_signals(features)
        state.signals = [signal_to_json(s) for s in signals]
        state.add_event(
            "research",
            AgentStatus.COMPLETED,
            f"Generated {len(signals)} signals",
            {"signals_count": len(signals)},
        )
    except Exception as exc:
        msg = f"Signal generation failed: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.add_event("research", AgentStatus.FAILED, msg)

    return state


# ---------------------------------------------------------------------------
# 2. Risk Agent -- evaluate signals against risk constraints
# ---------------------------------------------------------------------------


def risk_agent(state: ResearchState) -> ResearchState:
    """Evaluate signals against risk constraints and check circuit breakers."""
    state.add_event("risk", AgentStatus.RUNNING, "Evaluating risk...")

    if not state.signals:
        state.add_event(
            "risk", AgentStatus.COMPLETED, "No signals to evaluate"
        )
        return state

    try:
        import polars as pl

        from core.serialization import (
            risk_assessment_to_json,
            signal_from_json,
        )
        from risk.manager import RiskManager

        signals = [signal_from_json(s) for s in state.signals]

        risk_mgr = RiskManager()
        empty_positions = pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "weight": pl.Float64,
                "target_shares": pl.Float64,
                "target_value": pl.Float64,
            }
        )
        assessment = risk_mgr.evaluate(
            signals, empty_positions, state.initial_capital
        )
        state.risk_assessment = risk_assessment_to_json(assessment)

        n_approved = len(assessment.approved_signals)
        n_rejected = len(assessment.rejected_signals)
        state.add_event(
            "risk",
            AgentStatus.COMPLETED,
            f"{n_approved} signals approved, {n_rejected} rejected",
            {"approved": n_approved, "rejected": n_rejected},
        )

        if n_rejected > 0:
            state.human_approval_required = True
            state.add_event(
                "risk",
                AgentStatus.AWAITING_APPROVAL,
                "Some signals were rejected -- human approval required",
            )
    except Exception as exc:
        msg = f"Risk evaluation failed: {exc}"
        logger.warning(msg)
        state.errors.append(msg)
        state.add_event("risk", AgentStatus.FAILED, msg)
        # Fall through without risk filtering -- signals remain as-is

    return state


# ---------------------------------------------------------------------------
# 3. Validation Agent -- backtest + deflated Sharpe
# ---------------------------------------------------------------------------


def validation_agent(state: ResearchState) -> ResearchState:
    """Run backtest on approved signals and compute deflated Sharpe ratio."""
    state.add_event("validation", AgentStatus.RUNNING, "Running backtest...")

    # Determine which signals to use (approved if available, else all)
    try:
        from core.serialization import signal_from_json

        if state.risk_assessment and state.risk_assessment.get("approved_signals"):
            signals = [
                signal_from_json(s)
                for s in state.risk_assessment["approved_signals"]
            ]
        elif state.signals:
            signals = [signal_from_json(s) for s in state.signals]
        else:
            state.add_event(
                "validation", AgentStatus.COMPLETED, "No signals for backtest"
            )
            return state
    except Exception as exc:
        msg = f"Failed to deserialize signals: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.add_event("validation", AgentStatus.FAILED, msg)
        return state

    # -- Run backtest -------------------------------------------------------
    try:
        from core.adapters import prepare_signals_for_backtest
        from core.serialization import df_from_json
        from backtest.engine.vectorized import VectorizedBacktestEngine
        from config.settings import settings

        prices = df_from_json(state.prices) if state.prices else None
        if prices is None or prices.is_empty():
            state.add_event(
                "validation", AgentStatus.FAILED, "No price data for backtest"
            )
            return state

        signals_df, bt_prices = prepare_signals_for_backtest(signals, prices)
        engine = VectorizedBacktestEngine()
        bt_result = engine.run(
            signals_df,
            bt_prices,
            initial_capital=state.initial_capital,
            commission=settings.backtest.commission,
            slippage=settings.backtest.slippage,
        )
        state.backtest_result = bt_result.to_json()
    except Exception as exc:
        msg = f"Backtest failed: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.add_event("validation", AgentStatus.FAILED, msg)
        return state

    # -- Deflated Sharpe ratio ----------------------------------------------
    try:
        from backtest.validation import BacktestValidator

        sharpe = state.backtest_result.get("sharpe_ratio")
        if sharpe is not None:
            n_obs = len(state.backtest_result.get("equity_curve", []))
            vr = BacktestValidator.deflated_sharpe_ratio(
                sharpe=sharpe,
                n_trials=1,
                n_observations=max(n_obs, 2),
            )
            state.validation_result = {
                "is_valid": vr.is_valid,
                "deflated_sharpe": vr.deflated_sharpe,
                "original_sharpe": vr.original_sharpe,
                "p_value": vr.p_value,
                "n_trials": vr.n_trials,
                "warnings": vr.warnings,
            }
            state.add_event(
                "validation",
                AgentStatus.COMPLETED,
                f"Sharpe: {sharpe:.3f}, Deflated Sharpe: {vr.deflated_sharpe:.3f}",
            )
        else:
            state.add_event(
                "validation",
                AgentStatus.COMPLETED,
                "Backtest completed (no Sharpe available)",
            )
    except Exception as exc:
        msg = f"Validation (deflated Sharpe) failed: {exc}"
        logger.warning(msg)
        state.errors.append(msg)
        state.add_event("validation", AgentStatus.FAILED, msg)

    return state


# ---------------------------------------------------------------------------
# 4. Decay Agent -- signal decay analysis (IC curves, half-life)
# ---------------------------------------------------------------------------


def decay_agent(state: ResearchState) -> ResearchState:
    """Analyze signal decay: IC curves and half-life estimation."""
    state.add_event("decay", AgentStatus.RUNNING, "Analyzing signal decay...")

    try:
        from core.serialization import df_from_json, signal_from_json, signals_to_dataframe

        # Use approved signals if available
        if state.risk_assessment and state.risk_assessment.get("approved_signals"):
            signals = [
                signal_from_json(s)
                for s in state.risk_assessment["approved_signals"]
            ]
        elif state.signals:
            signals = [signal_from_json(s) for s in state.signals]
        else:
            state.signal_decay = {"note": "No signals for decay analysis"}
            state.add_event(
                "decay", AgentStatus.COMPLETED, "No signals for decay analysis"
            )
            return state

        if len(signals) < 10:
            state.signal_decay = {"note": "Too few signals for decay analysis"}
            state.add_event(
                "decay",
                AgentStatus.COMPLETED,
                f"Too few signals ({len(signals)}) for decay analysis",
            )
            return state

        from analytics.signal_decay import SignalDecayAnalyzer

        prices = df_from_json(state.prices) if state.prices else None
        if prices is None or prices.is_empty():
            state.signal_decay = {"note": "No price data for decay analysis"}
            state.add_event(
                "decay", AgentStatus.FAILED, "No price data for decay analysis"
            )
            return state

        analyzer = SignalDecayAnalyzer()
        sig_df = signals_to_dataframe(signals)
        ic_curve = analyzer.compute_ic_curve(sig_df, prices)
        state.signal_decay = analyzer.decay_summary(ic_curve)

        half_life = state.signal_decay.get("half_life_days", "N/A")
        state.add_event(
            "decay",
            AgentStatus.COMPLETED,
            f"Half-life: {half_life} days",
            {"half_life": half_life},
        )
    except Exception as exc:
        msg = f"Signal decay analysis failed: {exc}"
        logger.warning(msg)
        state.errors.append(msg)
        state.signal_decay = {"error": str(exc)}
        state.add_event("decay", AgentStatus.FAILED, msg)

    return state


# ---------------------------------------------------------------------------
# 5. Report Agent -- generate research report from accumulated state
# ---------------------------------------------------------------------------


def report_agent(state: ResearchState) -> ResearchState:
    """Generate a research report from all accumulated state."""
    state.add_event("report", AgentStatus.RUNNING, "Generating report...")

    try:
        sections: list[str] = []
        sections.append(f"<h1>Research Report: {state.ticker}</h1>")
        sections.append(f"<p>Strategy: {state.strategy_name}</p>")
        sections.append(
            f"<p>Period: {state.start_date} to {state.end_date}</p>"
        )
        sections.append(
            f"<p>Initial Capital: ${state.initial_capital:,.2f}</p>"
        )

        # Signals summary
        n_signals = len(state.signals)
        sections.append(f"<h2>Signals</h2><p>Total generated: {n_signals}</p>")

        # Risk assessment
        if state.risk_assessment:
            ra = state.risk_assessment
            n_approved = len(ra.get("approved_signals", []))
            n_rejected = len(ra.get("rejected_signals", []))
            sections.append(
                f"<h2>Risk Assessment</h2>"
                f"<p>Approved: {n_approved}, Rejected: {n_rejected}</p>"
                f"<p>VaR: {ra.get('portfolio_var', 'N/A')}, "
                f"CVaR: {ra.get('portfolio_cvar', 'N/A')}</p>"
            )
            if ra.get("warnings"):
                sections.append(
                    "<p>Warnings: "
                    + ", ".join(ra["warnings"])
                    + "</p>"
                )

        # Backtest results
        if state.backtest_result:
            bt = state.backtest_result
            sections.append(
                f"<h2>Backtest Results</h2>"
                f"<p>Total Return: {bt.get('total_return', 'N/A')}</p>"
                f"<p>Sharpe Ratio: {bt.get('sharpe_ratio', 'N/A')}</p>"
                f"<p>Max Drawdown: {bt.get('max_drawdown', 'N/A')}</p>"
                f"<p>Win Rate: {bt.get('win_rate', 'N/A')}</p>"
            )

        # Validation
        if state.validation_result:
            vr = state.validation_result
            sections.append(
                f"<h2>Validation</h2>"
                f"<p>Deflated Sharpe: {vr.get('deflated_sharpe', 'N/A')}</p>"
                f"<p>Valid: {vr.get('is_valid', 'N/A')}</p>"
                f"<p>p-value: {vr.get('p_value', 'N/A')}</p>"
            )

        # Signal decay
        if state.signal_decay:
            sd = state.signal_decay
            if "error" in sd or "note" in sd:
                sections.append(
                    f"<h2>Signal Decay</h2>"
                    f"<p>{sd.get('note', sd.get('error', ''))}</p>"
                )
            else:
                sections.append(
                    f"<h2>Signal Decay</h2>"
                    f"<p>Half-life: {sd.get('half_life_days', 'N/A')} days</p>"
                )

        # Errors
        if state.errors:
            sections.append(
                "<h2>Errors</h2><ul>"
                + "".join(f"<li>{e}</li>" for e in state.errors)
                + "</ul>"
            )

        state.research_report = "\n".join(sections)
        state.add_event("report", AgentStatus.COMPLETED, "Report generated")
    except Exception as exc:
        msg = f"Report generation failed: {exc}"
        logger.error(msg)
        state.errors.append(msg)
        state.research_report = f"<p>Report generation failed: {exc}</p>"
        state.add_event("report", AgentStatus.FAILED, msg)

    return state


# ---------------------------------------------------------------------------
# Conditional edge: approval gate
# ---------------------------------------------------------------------------


def approval_gate(state: ResearchState) -> str:
    """Conditional edge function for LangGraph.

    Returns:
        "continue" -- proceed to validation.
        "wait"     -- pause for human approval.
        "abort"    -- skip to report with partial results.
    """
    if not state.human_approval_required:
        return "continue"

    if state.human_approved is None:
        return "wait"
    if state.human_approved is True:
        return "continue"
    # human_approved is False
    return "abort"
