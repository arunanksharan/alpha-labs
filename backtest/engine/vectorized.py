"""Vectorized backtest engine — pure polars, no Python loops over dates.

Implements BaseBacktestEngine using fully vectorized polars operations for
high-throughput signal replay and performance attribution.
"""

from __future__ import annotations

import polars as pl

from analytics.returns import (
    compute_calmar,
    compute_cvar,
    compute_max_drawdown,
    compute_returns,
    compute_sharpe,
    compute_sortino,
    compute_var,
)
from config.settings import settings
from core.backtest import BacktestEngineRegistry, BacktestResult, BaseBacktestEngine


def _empty_backtest_result(
    initial_capital: float,
    commission: float,
    slippage: float,
) -> BacktestResult:
    """Return a flat BacktestResult with zero returns for edge cases."""
    today = "1970-01-01"
    equity_curve = pl.DataFrame(
        {"date": [today], "equity": [initial_capital]},
        schema={"date": pl.Utf8, "equity": pl.Float64},
    )
    trades = pl.DataFrame(
        schema={
            "date": pl.Utf8,
            "ticker": pl.Utf8,
            "side": pl.Utf8,
            "price": pl.Float64,
            "quantity": pl.Float64,
            "pnl": pl.Float64,
        }
    )
    monthly_returns = pl.DataFrame(
        schema={"year": pl.Int32, "month": pl.Int32, "return": pl.Float64}
    )
    return BacktestResult(
        strategy_name="vectorized",
        start_date=today,
        end_date=today,
        total_return=0.0,
        annualized_return=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        max_drawdown=0.0,
        calmar_ratio=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        equity_curve=equity_curve,
        trades=trades,
        monthly_returns=monthly_returns,
        var_95=0.0,
        cvar_95=0.0,
        transaction_costs=commission + slippage,
        slippage_model="fixed",
    )


@BacktestEngineRegistry.register
class VectorizedBacktestEngine(BaseBacktestEngine):
    """Fully vectorized backtest engine using polars — no Python date loops."""

    @property
    def name(self) -> str:
        return "vectorized"

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    def run(
        self,
        signals: pl.DataFrame,
        prices: pl.DataFrame,
        initial_capital: float = 100_000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ) -> BacktestResult:
        # --- 1. Early return guard ---
        if signals is None or prices is None or len(signals) == 0 or len(prices) == 0:
            return _empty_backtest_result(initial_capital, commission, slippage)

        # Ensure date columns are consistently typed (cast to Date if Utf8).
        signals = self._normalise_dates(signals)
        prices = self._normalise_dates(prices)

        # --- 2. Compute weights ---
        weights = (
            signals.select(
                pl.col("date"),
                pl.col("ticker"),
                (pl.col("direction") * pl.col("confidence")).alias("weight"),
            )
            .group_by(["date", "ticker"])
            .agg(pl.col("weight").sum())
        )
        # Normalise so sum(|w|) <= 1.0 per date
        weights = weights.with_columns(
            pl.col("weight").abs().sum().over("date").alias("abs_sum")
        ).with_columns(
            pl.when(pl.col("abs_sum") > 1.0)
            .then(pl.col("weight") / pl.col("abs_sum"))
            .otherwise(pl.col("weight"))
            .alias("weight")
        ).drop("abs_sum")

        # --- 3. Compute daily log returns per ticker ---
        tickers = prices.select("ticker").unique()
        returns_parts: list[pl.DataFrame] = []
        for ticker_val in tickers["ticker"].to_list():
            ticker_prices = (
                prices.filter(pl.col("ticker") == ticker_val)
                .sort("date")
                .select("date", "close")
            )
            if len(ticker_prices) < 2:
                continue
            ret_df = compute_returns(ticker_prices, method="log")
            ret_df = ret_df.with_columns(pl.lit(ticker_val).alias("ticker"))
            returns_parts.append(ret_df)

        if len(returns_parts) == 0:
            return _empty_backtest_result(initial_capital, commission, slippage)

        ticker_returns = pl.concat(returns_parts)

        # --- 4. Merge weights with returns ---
        merged = weights.join(ticker_returns, on=["date", "ticker"], how="inner")
        # Portfolio return per date = sum(weight * return)
        portfolio = (
            merged.with_columns(
                (pl.col("weight") * pl.col("returns")).alias("contrib")
            )
            .group_by("date")
            .agg(pl.col("contrib").sum().alias("port_return"))
            .sort("date")
        )

        if len(portfolio) == 0:
            return _empty_backtest_result(initial_capital, commission, slippage)

        # --- 5. Transaction costs ---
        # Build a full date x ticker weight grid (fill missing with 0).
        all_dates = portfolio.select("date").sort("date")
        all_tickers_in_weights = weights.select("ticker").unique()
        date_ticker_grid = all_dates.join(all_tickers_in_weights, how="cross")
        weight_grid = date_ticker_grid.join(
            weights, on=["date", "ticker"], how="left"
        ).with_columns(pl.col("weight").fill_null(0.0))

        # Previous day weight per ticker
        weight_grid = weight_grid.sort(["ticker", "date"]).with_columns(
            pl.col("weight").shift(1).over("ticker").fill_null(0.0).alias("prev_weight")
        )
        weight_grid = weight_grid.with_columns(
            (pl.col("weight") - pl.col("prev_weight")).abs().alias("delta_weight")
        )
        daily_cost = (
            weight_grid.group_by("date")
            .agg(pl.col("delta_weight").sum().alias("total_delta"))
            .with_columns(
                (pl.col("total_delta") * (commission + slippage)).alias("cost")
            )
            .select("date", "cost")
        )

        portfolio = portfolio.join(daily_cost, on="date", how="left").with_columns(
            pl.col("cost").fill_null(0.0)
        )
        portfolio = portfolio.with_columns(
            (pl.col("port_return") - pl.col("cost")).alias("port_return")
        )

        # --- 6. Equity curve ---
        portfolio = portfolio.sort("date").with_columns(
            (pl.col("port_return") + 1.0).cum_prod().alias("cum_factor")
        )
        portfolio = portfolio.with_columns(
            (pl.lit(initial_capital) * pl.col("cum_factor")).alias("equity")
        )
        equity_curve = portfolio.select(
            pl.col("date").cast(pl.Utf8),
            pl.col("equity"),
        )

        # --- 7. Trades ---
        trades_df = self._build_trades(weight_grid, prices, portfolio, initial_capital)

        # --- 8. Monthly returns ---
        monthly_returns = self._build_monthly_returns(portfolio)

        # --- 9. Metrics ---
        returns_df = portfolio.select(
            pl.col("date"),
            pl.col("port_return").alias("returns"),
        )
        n_days = len(returns_df)

        risk_free = settings.backtest.risk_free_rate

        sharpe = compute_sharpe(returns_df, risk_free_rate=risk_free) if n_days >= 2 else 0.0
        sortino = compute_sortino(returns_df, risk_free_rate=risk_free) if n_days >= 2 else 0.0
        max_dd = compute_max_drawdown(returns_df) if n_days >= 1 else 0.0
        calmar = compute_calmar(returns_df) if n_days >= 2 else 0.0
        var_95 = compute_var(returns_df) if n_days >= 2 else 0.0
        cvar_95 = compute_cvar(returns_df) if n_days >= 2 else 0.0

        final_equity = portfolio["equity"][-1]
        total_return = final_equity / initial_capital - 1.0
        annualized_return = (
            (1.0 + total_return) ** (252.0 / n_days) - 1.0
            if n_days > 0
            else 0.0
        )

        # Win rate / profit factor from trades
        win_rate, profit_factor = self._trade_stats(trades_df)

        start_date = str(portfolio["date"].min())
        end_date = str(portfolio["date"].max())

        return BacktestResult(
            strategy_name="vectorized",
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            equity_curve=equity_curve,
            trades=trades_df,
            monthly_returns=monthly_returns,
            var_95=var_95,
            cvar_95=cvar_95,
            transaction_costs=commission + slippage,
            slippage_model="fixed",
        )

    # ------------------------------------------------------------------
    # walk_forward
    # ------------------------------------------------------------------
    def walk_forward(
        self,
        signals: pl.DataFrame,
        prices: pl.DataFrame,
        train_window: int = 252,
        test_window: int = 63,
        **kwargs,
    ) -> list[BacktestResult]:
        prices = self._normalise_dates(prices)
        signals = self._normalise_dates(signals)

        sorted_dates = prices.select("date").unique().sort("date")["date"].to_list()
        results: list[BacktestResult] = []

        i = 0
        while i + train_window + test_window <= len(sorted_dates):
            test_start = sorted_dates[i + train_window]
            test_end = sorted_dates[i + train_window + test_window - 1]

            test_prices = prices.filter(
                (pl.col("date") >= test_start) & (pl.col("date") <= test_end)
            )
            test_signals = signals.filter(
                (pl.col("date") >= test_start) & (pl.col("date") <= test_end)
            )

            result = self.run(test_signals, test_prices, **kwargs)
            results.append(result)
            i += test_window

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_dates(df: pl.DataFrame) -> pl.DataFrame:
        """Normalize date column to pl.Date regardless of input type."""
        if "date" not in df.columns:
            return df
        dtype = df["date"].dtype
        if dtype == pl.Utf8:
            df = df.with_columns(pl.col("date").str.to_date().alias("date"))
        elif isinstance(dtype, pl.Datetime):
            df = df.with_columns(pl.col("date").dt.date().alias("date"))
        return df

    @staticmethod
    def _build_trades(
        weight_grid: pl.DataFrame,
        prices: pl.DataFrame,
        portfolio: pl.DataFrame,
        initial_capital: float,
    ) -> pl.DataFrame:
        """Detect weight changes and produce a trades DataFrame."""
        changed = weight_grid.filter(pl.col("delta_weight") > 1e-12)
        if len(changed) == 0:
            return pl.DataFrame(
                schema={
                    "date": pl.Utf8,
                    "ticker": pl.Utf8,
                    "side": pl.Utf8,
                    "price": pl.Float64,
                    "quantity": pl.Float64,
                    "pnl": pl.Float64,
                }
            )

        # Determine side
        changed = changed.with_columns(
            pl.when(pl.col("weight") > pl.col("prev_weight"))
            .then(pl.lit("buy"))
            .otherwise(pl.lit("sell"))
            .alias("side")
        )

        # Attach close price
        price_close = prices.select("date", "ticker", "close").rename({"close": "price"})
        changed = changed.join(price_close, on=["date", "ticker"], how="left")

        # Attach equity for quantity calc
        equity_map = portfolio.select("date", "equity")
        changed = changed.join(equity_map, on="date", how="left")

        # Quantity = |delta_weight| * equity / price
        changed = changed.with_columns(
            (pl.col("delta_weight") * pl.col("equity") / pl.col("price"))
            .fill_null(0.0)
            .alias("quantity")
        )

        # PnL approximation: return * weight * equity for that date
        port_return_map = portfolio.select(
            pl.col("date"), pl.col("port_return").alias("_day_ret")
        )
        changed = changed.join(port_return_map, on="date", how="left")
        changed = changed.with_columns(
            (pl.col("_day_ret").fill_null(0.0) * pl.col("weight") * pl.col("equity"))
            .alias("pnl")
        )

        return changed.select(
            pl.col("date").cast(pl.Utf8),
            "ticker",
            "side",
            "price",
            "quantity",
            "pnl",
        )

    @staticmethod
    def _build_monthly_returns(portfolio: pl.DataFrame) -> pl.DataFrame:
        """Group equity by year/month; return = last/first - 1."""
        df = portfolio.select("date", "equity").with_columns(
            pl.col("date").dt.year().alias("year"),
            pl.col("date").dt.month().alias("month"),
        )
        monthly = (
            df.group_by(["year", "month"])
            .agg(
                pl.col("equity").first().alias("first_eq"),
                pl.col("equity").last().alias("last_eq"),
            )
            .with_columns(
                ((pl.col("last_eq") / pl.col("first_eq")) - 1.0).alias("return")
            )
            .select("year", "month", "return")
            .sort(["year", "month"])
        )
        return monthly

    @staticmethod
    def _trade_stats(trades: pl.DataFrame) -> tuple[float, float]:
        """Compute win_rate and profit_factor from trades DataFrame."""
        if len(trades) == 0:
            return 0.0, 0.0

        pnls = trades["pnl"]
        total = len(pnls)
        wins = pnls.filter(pnls > 0.0)
        losses = pnls.filter(pnls < 0.0)

        win_rate = float(len(wins)) / total if total > 0 else 0.0

        sum_wins = float(wins.sum()) if len(wins) > 0 else 0.0
        sum_losses = float(losses.sum()) if len(losses) > 0 else 0.0

        if sum_losses == 0.0:
            profit_factor = float("inf") if sum_wins > 0 else 0.0
        else:
            profit_factor = sum_wins / abs(sum_losses)

        return win_rate, profit_factor
