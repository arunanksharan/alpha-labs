"""Paper trading simulator with position tracking and performance reporting.

Executes signals against simulated prices without touching real markets,
maintaining a full position book, cash ledger, and historical P&L series.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import polars as pl

from core.strategies import Signal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PaperPortfolio:
    """Snapshot of a paper-trading portfolio."""

    cash: float
    positions: dict[str, float]  # ticker -> shares
    history: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Paper trader
# ---------------------------------------------------------------------------


class PaperTrader:
    """Simulated paper trading with position tracking.

    Maintains a :class:`PaperPortfolio` that is updated via
    :meth:`execute_signals`.  Provides convenience methods for
    portfolio valuation and performance reporting.

    Args:
        initial_capital: Starting cash balance in dollars.
    """

    def __init__(self, initial_capital: float = 100_000.0) -> None:
        self._initial_capital = initial_capital
        self._portfolio = PaperPortfolio(
            cash=initial_capital,
            positions={},
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def portfolio(self) -> PaperPortfolio:
        """Return the current portfolio snapshot."""
        return self._portfolio

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_signals(
        self,
        signals: list[Signal],
        prices: dict[str, float],
    ) -> PaperPortfolio:
        """Convert signals to orders and execute at the given prices.

        Positive ``direction`` in a signal is treated as a buy, negative as
        a sell.  The traded quantity is ``direction * confidence * 100``
        shares (a simple heuristic; production systems would use a position
        sizer).

        Args:
            signals: List of :class:`~core.strategies.Signal` objects.
            prices: Mapping of ticker to current price.

        Returns:
            The updated :class:`PaperPortfolio`.
        """
        for signal in signals:
            ticker = signal.ticker
            price = prices.get(ticker)
            if price is None:
                logger.warning("No price for %s -- skipping signal", ticker)
                continue

            # Determine quantity from direction and confidence
            quantity = signal.direction * signal.confidence * 100.0

            if quantity == 0.0:
                continue

            trade_value = quantity * price

            # Check if we have enough cash for a buy
            if trade_value > 0.0 and trade_value > self._portfolio.cash:
                # Scale down to affordable quantity
                affordable_qty = self._portfolio.cash / price
                if affordable_qty < 1.0:
                    logger.warning(
                        "Insufficient cash for %s (need %.2f, have %.2f)",
                        ticker,
                        trade_value,
                        self._portfolio.cash,
                    )
                    continue
                quantity = affordable_qty
                trade_value = quantity * price

            # Update positions
            current_shares = self._portfolio.positions.get(ticker, 0.0)
            new_shares = current_shares + quantity
            if abs(new_shares) < 1e-10:
                self._portfolio.positions.pop(ticker, None)
            else:
                self._portfolio.positions[ticker] = new_shares

            # Update cash
            self._portfolio.cash -= trade_value

            logger.info(
                "%s %+.2f shares of %s @ %.4f (cash=%.2f)",
                "BUY" if quantity > 0 else "SELL",
                quantity,
                ticker,
                price,
                self._portfolio.cash,
            )

        # Record snapshot
        snapshot = {
            "date": date.today().isoformat(),
            "cash": self._portfolio.cash,
            "positions": dict(self._portfolio.positions),
            "portfolio_value": self.get_portfolio_value(prices),
        }
        self._portfolio.history.append(snapshot)

        return self._portfolio

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    def get_portfolio_value(self, prices: dict[str, float]) -> float:
        """Compute total portfolio value at current prices.

        Args:
            prices: Mapping of ticker to current market price.

        Returns:
            ``cash + sum(shares * price)`` for all held positions.
        """
        position_value = 0.0
        for ticker, shares in self._portfolio.positions.items():
            price = prices.get(ticker, 0.0)
            position_value += shares * price
        return self._portfolio.cash + position_value

    # ------------------------------------------------------------------
    # Performance reporting
    # ------------------------------------------------------------------

    def get_performance(self) -> pl.DataFrame:
        """Build a performance summary from the trading history.

        Returns:
            DataFrame with columns ``[date, portfolio_value, daily_return,
            cumulative_return]``.
        """
        if not self._portfolio.history:
            return pl.DataFrame(
                {
                    "date": pl.Series([], dtype=pl.Utf8),
                    "portfolio_value": pl.Series([], dtype=pl.Float64),
                    "daily_return": pl.Series([], dtype=pl.Float64),
                    "cumulative_return": pl.Series([], dtype=pl.Float64),
                }
            )

        dates: list[str] = []
        values: list[float] = []
        for snap in self._portfolio.history:
            dates.append(snap["date"])
            values.append(snap["portfolio_value"])

        values_arr = np.array(values, dtype=np.float64)

        # Daily returns
        daily_returns = np.zeros_like(values_arr)
        daily_returns[0] = (values_arr[0] - self._initial_capital) / self._initial_capital
        if len(values_arr) > 1:
            daily_returns[1:] = np.diff(values_arr) / values_arr[:-1]

        # Cumulative returns
        cumulative = (values_arr / self._initial_capital) - 1.0

        return pl.DataFrame(
            {
                "date": dates,
                "portfolio_value": values_arr.tolist(),
                "daily_return": daily_returns.tolist(),
                "cumulative_return": cumulative.tolist(),
            }
        )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset portfolio to the initial state."""
        self._portfolio = PaperPortfolio(
            cash=self._initial_capital,
            positions={},
        )
        logger.info("Paper trader reset to initial capital %.2f", self._initial_capital)
