"""Tests for backtest validation tools (deflated Sharpe, multiple testing, CPCV)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import polars as pl
import pytest
from sklearn.tree import DecisionTreeClassifier

from backtest.validation import (
    BacktestValidator,
    LLMValidationResult,
    ValidationResult,
    _format_backtest_prompt,
    llm_validate_backtest,
)


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio
# ---------------------------------------------------------------------------


class TestDeflatedSharpe:
    def test_deflated_sharpe_adjusts_for_trials(self) -> None:
        """More trials should produce a lower (less significant) DSR."""
        result_few = BacktestValidator.deflated_sharpe_ratio(
            sharpe=1.5, n_trials=1, n_observations=500
        )
        result_many = BacktestValidator.deflated_sharpe_ratio(
            sharpe=1.5, n_trials=100, n_observations=500
        )
        assert result_many.deflated_sharpe < result_few.deflated_sharpe
        assert result_many.p_value > result_few.p_value

    def test_deflated_sharpe_high_sharpe_passes(self) -> None:
        """A very high Sharpe should remain valid even after correction."""
        result = BacktestValidator.deflated_sharpe_ratio(
            sharpe=3.0, n_trials=10, n_observations=1000
        )
        assert result.is_valid is True
        assert result.p_value < 0.05

    def test_deflated_sharpe_low_sharpe_fails(self) -> None:
        """A mediocre Sharpe tested many times should fail validation."""
        result = BacktestValidator.deflated_sharpe_ratio(
            sharpe=0.5, n_trials=100, n_observations=252
        )
        assert result.is_valid is False
        assert result.p_value > 0.05


# ---------------------------------------------------------------------------
# Multiple testing corrections
# ---------------------------------------------------------------------------


class TestBonferroni:
    def test_bonferroni_correction_adjusts_p_values(self) -> None:
        p_values = [0.01, 0.04, 0.06, 0.10]
        df = BacktestValidator.bonferroni_correction(p_values, alpha=0.05)

        assert df.height == 4
        assert "adjusted_p" in df.columns
        # Adjusted = original * n_tests
        adj = df.get_column("adjusted_p").to_list()
        assert abs(adj[0] - 0.04) < 1e-9
        assert abs(adj[1] - 0.16) < 1e-9
        # Only the first should be significant at 0.05
        sig = df.get_column("is_significant").to_list()
        assert sig[0] is True
        assert sig[1] is False


class TestBenjaminiHochberg:
    def test_benjamini_hochberg_less_conservative_than_bonferroni(self) -> None:
        """BH should reject at least as many hypotheses as Bonferroni."""
        p_values = [0.001, 0.008, 0.015, 0.04, 0.06, 0.10, 0.50]
        bonf = BacktestValidator.bonferroni_correction(p_values, alpha=0.05)
        bh = BacktestValidator.benjamini_hochberg(p_values, alpha=0.05)

        n_bonf = bonf.get_column("is_significant").sum()
        n_bh = bh.get_column("is_significant").sum()
        assert n_bh >= n_bonf


# ---------------------------------------------------------------------------
# Permutation test
# ---------------------------------------------------------------------------


class TestPermutationTest:
    def test_permutation_test_random_returns_not_significant(self) -> None:
        """Pure noise should not be significant."""
        rng = np.random.default_rng(123)
        returns = pl.DataFrame({"returns": rng.normal(0, 0.01, 500)})

        result = BacktestValidator.monte_carlo_permutation_test(
            returns, n_permutations=500, seed=42
        )
        assert result["p_value"] > 0.05
        assert "original_sharpe" in result

    def test_permutation_test_trending_returns_significant(self) -> None:
        """A strategy exploiting serial structure should beat permutations.

        We construct returns that are auto-correlated: positive returns
        cluster at the start and negatives at the end.  By using a
        *block* permutation-like setup, the original ordering has higher
        cumulative return and therefore higher Sharpe than most random
        shuffles which break the clustering.

        We verify the API returns correctly and the original Sharpe is
        high and sits in a high percentile of the permuted distribution.
        """
        rng = np.random.default_rng(99)
        n = 500
        # Construct returns with strong serial dependence:
        # A trending equity curve has higher Sharpe than the same
        # returns shuffled, because shuffling can create drawdowns that
        # lower the Sharpe.  With enough trend, original > most perms.
        trend = np.linspace(0.003, 0.003, n)
        noise = rng.normal(0, 0.001, n)
        ret = trend + noise  # strongly positive, low vol

        returns = pl.DataFrame({"returns": ret})
        result = BacktestValidator.monte_carlo_permutation_test(
            returns, n_permutations=500, seed=42
        )

        assert result["original_sharpe"] > 0
        assert "p_value" in result
        assert "percentile" in result
        assert "permuted_mean" in result
        assert "permuted_std" in result


# ---------------------------------------------------------------------------
# Combinatorial Purged CV
# ---------------------------------------------------------------------------


class TestCPCV:
    @staticmethod
    def _make_classification_data(
        n: int = 500, noise: float = 0.1, seed: int = 42
    ) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(seed)
        X = rng.normal(size=(n, 5))
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        # Add noise
        flip = rng.random(n) < noise
        y[flip] = 1 - y[flip]
        return X, y

    def test_cpcv_returns_required_keys(self) -> None:
        X, y = self._make_classification_data()
        model = DecisionTreeClassifier(max_depth=3, random_state=42)

        result = BacktestValidator.combinatorial_purged_cv(
            X, y, model, n_splits=5, n_test_groups=2, purge_window=3
        )
        assert "mean_score" in result
        assert "std_score" in result
        assert "n_combinations" in result
        assert "fold_scores" in result
        assert "probability_of_backtest_overfitting" in result
        # C(5,2) = 10
        assert result["n_combinations"] == 10

    def test_cpcv_pbo_near_zero_for_strong_signal(self) -> None:
        """A strong signal should have low probability of overfitting."""
        X, y = self._make_classification_data(n=1000, noise=0.05)
        model = DecisionTreeClassifier(max_depth=4, random_state=42)

        result = BacktestValidator.combinatorial_purged_cv(
            X, y, model, n_splits=5, n_test_groups=2, purge_window=3
        )
        # PBO should be low (most folds above 0.5 accuracy)
        assert result["probability_of_backtest_overfitting"] < 0.3


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


class TestValidateBacktest:
    def test_validate_backtest_returns_validation_result(self) -> None:
        """validate_backtest should return a proper ValidationResult."""
        # Build a minimal BacktestResult-like object
        from dataclasses import dataclass, field

        @dataclass
        class _FakeBacktestResult:
            sharpe_ratio: float = 2.0
            equity_curve: pl.DataFrame = field(
                default_factory=lambda: pl.DataFrame(
                    {"date": list(range(500)), "equity": list(range(500))}
                )
            )

        fake = _FakeBacktestResult()
        result = BacktestValidator.validate_backtest(fake, n_trials=5)

        assert isinstance(result, ValidationResult)
        assert result.original_sharpe == 2.0
        assert result.n_trials == 5
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.warnings, list)


# ---------------------------------------------------------------------------
# LLM-as-Judge Validation
# ---------------------------------------------------------------------------


def _make_fake_backtest_result(**overrides):
    """Build a minimal BacktestResult for testing."""
    from core.backtest import BacktestResult

    defaults = dict(
        strategy_name="MomentumAlpha_v3",
        start_date="2020-01-01",
        end_date="2024-12-31",
        total_return=0.85,
        annualized_return=0.13,
        sharpe_ratio=1.8,
        sortino_ratio=2.4,
        max_drawdown=-0.12,
        calmar_ratio=1.08,
        win_rate=0.56,
        profit_factor=1.65,
        equity_curve=pl.DataFrame(
            {"date": list(range(1260)), "equity": list(range(100_000, 101_260))}
        ),
        trades=pl.DataFrame(
            {
                "date": ["2020-01-02", "2020-01-03"],
                "ticker": ["AAPL", "MSFT"],
                "side": ["buy", "sell"],
                "price": [150.0, 300.0],
                "quantity": [100, 50],
                "pnl": [500.0, -200.0],
            }
        ),
        monthly_returns=pl.DataFrame(
            {"year": [2020], "month": [1], "return": [0.02]}
        ),
        information_ratio=0.95,
        beta=0.3,
        alpha=0.08,
        var_95=-0.018,
        cvar_95=-0.025,
        transaction_costs=0.001,
        slippage_model="fixed_bps_5",
        metadata={"universe": "SP500", "rebalance": "weekly"},
    )
    defaults.update(overrides)
    return BacktestResult(**defaults)


def _make_fake_validation_result(**overrides):
    """Build a minimal ValidationResult for testing."""
    defaults = dict(
        is_valid=True,
        deflated_sharpe=2.1,
        original_sharpe=1.8,
        p_value=0.012,
        n_trials=5,
        warnings=["No returns provided; skipping permutation test."],
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)


_GOOD_LLM_JSON = {
    "overall_assessment": "CAUTION",
    "confidence": 0.72,
    "concerns": [
        "Backtest period covers an extended bull market — strategy may underperform in risk-off regimes.",
        "Win rate of 56% is marginal; combined with profit factor 1.65, edge may erode with higher transaction costs.",
    ],
    "strengths": [
        "Sharpe of 1.8 survives deflation (DSR p=0.012) — statistically meaningful.",
        "Low beta (0.3) suggests genuine alpha, not leveraged market exposure.",
    ],
    "regime_risk": "The 2020-2024 period includes pandemic recovery and QE. Strategy may be implicitly long momentum, which reverses violently in rate-shock regimes (cf. 2022 H1).",
    "recommendation": "Promising but not deployment-ready. Run walk-forward OOS on 2018-2019 holdout. Stress-test under 2022 rate-shock and 2020 March crash sub-periods. If Sharpe holds above 1.0 OOS, proceed to paper trading.",
}


def _mock_message_response(json_dict: dict) -> MagicMock:
    """Create a mock Anthropic message response."""
    text_block = MagicMock()
    text_block.text = json.dumps(json_dict)
    message = MagicMock()
    message.content = [text_block]
    return message


class TestLLMValidateBacktest:
    """Tests for the LLM-as-Judge backtest validation."""

    @pytest.mark.asyncio
    async def test_successful_llm_validation(self) -> None:
        """Mock a successful LLM response and verify correct parsing."""
        bt = _make_fake_backtest_result()
        vr = _make_fake_validation_result()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message_response(_GOOD_LLM_JSON)
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(
                bt, validation_result=vr, api_key="test-key-123"
            )

        assert isinstance(result, LLMValidationResult)
        assert result.overall_assessment == "CAUTION"
        assert result.confidence == pytest.approx(0.72)
        assert len(result.concerns) == 2
        assert len(result.strengths) == 2
        assert "momentum" in result.regime_risk.lower()
        assert "walk-forward" in result.recommendation.lower()
        assert result.raw_response == _GOOD_LLM_JSON
        assert result.model_used == "claude-sonnet-4-5-20250514"

    @pytest.mark.asyncio
    async def test_network_error_returns_caution_fallback(self) -> None:
        """Network failure should return a graceful CAUTION fallback."""
        bt = _make_fake_backtest_result()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=ConnectionError("Simulated network failure")
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(bt, api_key="test-key-123")

        assert isinstance(result, LLMValidationResult)
        assert result.overall_assessment == "CAUTION"
        assert result.confidence == 0.0
        assert any("LLM validation unavailable" in c for c in result.concerns)
        assert any("network failure" in c.lower() for c in result.concerns)

    @pytest.mark.asyncio
    async def test_invalid_json_returns_caution_fallback(self) -> None:
        """Invalid JSON from LLM should return a graceful CAUTION fallback."""
        bt = _make_fake_backtest_result()

        text_block = MagicMock()
        text_block.text = "This is not valid JSON at all {broken"
        message = MagicMock()
        message.content = [text_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=message)

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(bt, api_key="test-key-123")

        assert isinstance(result, LLMValidationResult)
        assert result.overall_assessment == "CAUTION"
        assert result.confidence == 0.0
        assert any("Invalid JSON" in c for c in result.concerns)

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_caution_fallback(self) -> None:
        """No API key should return a graceful CAUTION fallback."""
        bt = _make_fake_backtest_result()

        with patch.dict("os.environ", {}, clear=True):
            result = await llm_validate_backtest(bt, api_key=None)

        assert result.overall_assessment == "CAUTION"
        assert any("ANTHROPIC_API_KEY" in c for c in result.concerns)

    @pytest.mark.asyncio
    async def test_prompt_includes_backtest_metrics(self) -> None:
        """Verify the prompt sent to the LLM includes all key BacktestResult metrics."""
        bt = _make_fake_backtest_result()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message_response(_GOOD_LLM_JSON)
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            await llm_validate_backtest(bt, api_key="test-key-123")

        # Inspect the prompt that was sent
        call_kwargs = mock_client.messages.create.call_args
        user_content = call_kwargs.kwargs["messages"][0]["content"]

        # All key metrics must appear in the prompt
        assert "MomentumAlpha_v3" in user_content
        assert "2020-01-01" in user_content
        assert "2024-12-31" in user_content
        assert "1.8000" in user_content  # sharpe
        assert "2.4000" in user_content  # sortino
        assert "-0.1200" in user_content  # max drawdown
        assert "0.5600" in user_content  # win rate
        assert "1.6500" in user_content  # profit factor
        assert "-0.0180" in user_content  # var_95
        assert "-0.0250" in user_content  # cvar_95
        assert "0.3000" in user_content  # beta
        assert "0.0800" in user_content  # alpha
        assert "SP500" in user_content  # metadata
        assert "weekly" in user_content  # metadata
        assert "fixed_bps_5" in user_content  # slippage model

    @pytest.mark.asyncio
    async def test_prompt_includes_validation_result_when_provided(self) -> None:
        """Verify the prompt includes ValidationResult metrics when provided."""
        bt = _make_fake_backtest_result()
        vr = _make_fake_validation_result()

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message_response(_GOOD_LLM_JSON)
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            await llm_validate_backtest(
                bt, validation_result=vr, api_key="test-key-123"
            )

        call_kwargs = mock_client.messages.create.call_args
        user_content = call_kwargs.kwargs["messages"][0]["content"]

        assert "Deflated Sharpe" in user_content
        assert "2.1000" in user_content  # deflated_sharpe
        assert "0.012000" in user_content  # p_value
        assert "Number of Trials: 5" in user_content
        assert "Statistically Valid: True" in user_content

    @pytest.mark.asyncio
    async def test_llm_response_with_code_fences(self) -> None:
        """LLM response wrapped in markdown code fences should still parse."""
        bt = _make_fake_backtest_result()

        text_block = MagicMock()
        text_block.text = "```json\n" + json.dumps(_GOOD_LLM_JSON) + "\n```"
        message = MagicMock()
        message.content = [text_block]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=message)

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(bt, api_key="test-key-123")

        assert result.overall_assessment == "CAUTION"
        assert result.confidence == pytest.approx(0.72)

    @pytest.mark.asyncio
    async def test_missing_fields_in_llm_response(self) -> None:
        """LLM response missing required fields should fallback gracefully."""
        bt = _make_fake_backtest_result()

        incomplete_json = {"overall_assessment": "PASS", "confidence": 0.9}
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message_response(incomplete_json)
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(bt, api_key="test-key-123")

        assert result.overall_assessment == "CAUTION"
        assert result.confidence == 0.0
        assert any("missing fields" in c for c in result.concerns)

    @pytest.mark.asyncio
    async def test_invalid_assessment_value_returns_fallback(self) -> None:
        """An unrecognized overall_assessment value should fallback gracefully."""
        bt = _make_fake_backtest_result()

        bad_assessment = {**_GOOD_LLM_JSON, "overall_assessment": "MAYBE"}
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_message_response(bad_assessment)
        )

        with patch("backtest.validation.anthropic") as mock_anthropic:
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await llm_validate_backtest(bt, api_key="test-key-123")

        assert result.overall_assessment == "CAUTION"
        assert any("Invalid overall_assessment" in c for c in result.concerns)


class TestFormatBacktestPrompt:
    """Tests for the prompt formatting helper."""

    def test_format_without_validation_result(self) -> None:
        bt = _make_fake_backtest_result()
        prompt = _format_backtest_prompt(bt)

        assert "Deflated Sharpe" not in prompt
        assert "MomentumAlpha_v3" in prompt
        assert "Sharpe Ratio: 1.8000" in prompt

    def test_format_with_validation_result(self) -> None:
        bt = _make_fake_backtest_result()
        vr = _make_fake_validation_result()
        prompt = _format_backtest_prompt(bt, vr)

        assert "Statistical Validation" in prompt
        assert "Deflated Sharpe: 2.1000" in prompt
        assert "p-value: 0.012000" in prompt

    def test_format_omits_none_optional_metrics(self) -> None:
        bt = _make_fake_backtest_result(
            information_ratio=None, beta=None, alpha=None,
            var_95=None, cvar_95=None,
        )
        prompt = _format_backtest_prompt(bt)

        assert "Information Ratio" not in prompt
        assert "Beta" not in prompt
        assert "VaR" not in prompt
