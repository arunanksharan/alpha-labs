"""Tear sheet generator for backtest results.

Produces visual reports: equity curve, drawdown, monthly heatmap, metrics table.
Saves as self-contained HTML or individual PNGs.
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import polars as pl
from matplotlib.figure import Figure

from analytics.returns import compute_drawdown, compute_returns
from core.backtest import BacktestResult

logger = logging.getLogger(__name__)

_COLORS = {
    "equity": "#8b5cf6",
    "drawdown": "#ef4444",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral": "#6b7280",
    "grid": "#374151",
    "bg": "#111827",
    "text": "#f9fafb",
}


def _style_ax(ax: plt.Axes) -> None:
    """Apply dark theme styling to an axis."""
    ax.set_facecolor(_COLORS["bg"])
    ax.tick_params(colors=_COLORS["text"], which="both")
    ax.xaxis.label.set_color(_COLORS["text"])
    ax.yaxis.label.set_color(_COLORS["text"])
    ax.title.set_color(_COLORS["text"])
    ax.grid(True, alpha=0.2, color=_COLORS["grid"])
    for spine in ax.spines.values():
        spine.set_color(_COLORS["grid"])


class TearSheet:
    """Generate visual tear sheet from a BacktestResult."""

    def __init__(self, result: BacktestResult) -> None:
        self._result = result

    def equity_curve_plot(self) -> Figure:
        """Line plot of portfolio equity over time."""
        ec = self._result.equity_curve
        if ec.is_empty():
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14)
            return fig

        dates = ec["date"].to_list()
        equity = ec["equity"].to_list()

        fig, ax = plt.subplots(figsize=(12, 4))
        fig.patch.set_facecolor(_COLORS["bg"])
        _style_ax(ax)

        ax.plot(dates, equity, color=_COLORS["equity"], linewidth=1.5)
        ax.fill_between(dates, equity, alpha=0.1, color=_COLORS["equity"])
        ax.set_title(f"{self._result.strategy_name} — Equity Curve", fontsize=14, fontweight="bold")
        ax.set_ylabel("Equity ($)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

        fig.tight_layout()
        return fig

    def drawdown_plot(self) -> Figure:
        """Filled area plot of drawdown over time."""
        ec = self._result.equity_curve
        if ec.is_empty() or len(ec) < 2:
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14)
            return fig

        returns_df = compute_returns(ec.select(["date", "equity"]))
        dd_df = compute_drawdown(returns_df)

        dates = dd_df["date"].to_list()
        dd = dd_df["drawdown"].to_list()

        fig, ax = plt.subplots(figsize=(12, 3))
        fig.patch.set_facecolor(_COLORS["bg"])
        _style_ax(ax)

        ax.fill_between(dates, dd, 0, color=_COLORS["drawdown"], alpha=0.4)
        ax.plot(dates, dd, color=_COLORS["drawdown"], linewidth=1.0)
        ax.set_title("Drawdown", fontsize=14, fontweight="bold")
        ax.set_ylabel("Drawdown")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1%}"))

        fig.tight_layout()
        return fig

    def monthly_returns_heatmap(self) -> Figure:
        """Heatmap of monthly returns (year x month)."""
        mr = self._result.monthly_returns
        if mr.is_empty():
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=14)
            return fig

        years = sorted(mr["year"].unique().to_list())
        months = list(range(1, 13))
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        grid = np.full((len(years), 12), np.nan)
        for row in mr.iter_rows(named=True):
            y_idx = years.index(row["year"])
            m_idx = row["month"] - 1
            grid[y_idx, m_idx] = row["return"]

        fig, ax = plt.subplots(figsize=(12, max(3, len(years) * 0.6)))
        fig.patch.set_facecolor(_COLORS["bg"])
        _style_ax(ax)

        vmax = max(abs(np.nanmin(grid)) if not np.all(np.isnan(grid)) else 0.1,
                   abs(np.nanmax(grid)) if not np.all(np.isnan(grid)) else 0.1)
        im = ax.imshow(grid, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

        ax.set_xticks(range(12))
        ax.set_xticklabels(month_names)
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels([str(y) for y in years])
        ax.set_title("Monthly Returns", fontsize=14, fontweight="bold")

        for i in range(len(years)):
            for j in range(12):
                val = grid[i, j]
                if not np.isnan(val):
                    color = "white" if abs(val) > vmax * 0.5 else "black"
                    ax.text(j, i, f"{val:.1%}", ha="center", va="center",
                            fontsize=8, color=color)

        fig.colorbar(im, ax=ax, shrink=0.8, format=mticker.FuncFormatter(lambda x, _: f"{x:.1%}"))
        fig.tight_layout()
        return fig

    def metrics_table(self) -> Figure:
        """Tabular summary of key metrics."""
        r = self._result
        metrics = [
            ("Total Return", f"{r.total_return:.2%}"),
            ("Annualized Return", f"{r.annualized_return:.2%}"),
            ("Sharpe Ratio", f"{r.sharpe_ratio:.2f}"),
            ("Sortino Ratio", f"{r.sortino_ratio:.2f}"),
            ("Max Drawdown", f"{r.max_drawdown:.2%}"),
            ("Calmar Ratio", f"{r.calmar_ratio:.2f}"),
            ("Win Rate", f"{r.win_rate:.1%}"),
            ("Profit Factor", f"{r.profit_factor:.2f}"),
        ]
        if r.var_95 is not None:
            metrics.append(("VaR (95%)", f"{r.var_95:.4f}"))
        if r.cvar_95 is not None:
            metrics.append(("CVaR (95%)", f"{r.cvar_95:.4f}"))

        fig, ax = plt.subplots(figsize=(6, max(3, len(metrics) * 0.4)))
        fig.patch.set_facecolor(_COLORS["bg"])
        ax.set_facecolor(_COLORS["bg"])
        ax.axis("off")

        table = ax.table(
            cellText=[[m, v] for m, v in metrics],
            colLabels=["Metric", "Value"],
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.0, 1.5)

        for key, cell in table.get_celld().items():
            cell.set_edgecolor(_COLORS["grid"])
            if key[0] == 0:
                cell.set_facecolor("#1f2937")
                cell.set_text_props(color=_COLORS["text"], fontweight="bold")
            else:
                cell.set_facecolor(_COLORS["bg"])
                cell.set_text_props(color=_COLORS["text"])

        ax.set_title(
            f"{r.strategy_name} — Performance Metrics",
            fontsize=14, fontweight="bold", color=_COLORS["text"], pad=20,
        )
        fig.tight_layout()
        return fig

    def save_html(self, path: Path | str) -> None:
        """Save all plots as a self-contained HTML page."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        figures = [
            ("Metrics", self.metrics_table()),
            ("Equity Curve", self.equity_curve_plot()),
            ("Drawdown", self.drawdown_plot()),
            ("Monthly Returns", self.monthly_returns_heatmap()),
        ]

        images_html = []
        for title, fig in figures:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode("utf-8")
            images_html.append(
                f'<div style="margin:20px 0;">'
                f'<img src="data:image/png;base64,{b64}" style="max-width:100%;"/>'
                f'</div>'
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{self._result.strategy_name} — Tear Sheet</title>
<style>
  body {{ background: {_COLORS['bg']}; color: {_COLORS['text']}; font-family: 'Geist', system-ui, sans-serif; padding: 40px; max-width: 1200px; margin: 0 auto; }}
  h1 {{ color: {_COLORS['equity']}; }}
</style>
</head>
<body>
<h1>{self._result.strategy_name} — Tear Sheet</h1>
<p>{self._result.start_date} to {self._result.end_date}</p>
{''.join(images_html)}
</body>
</html>"""

        path.write_text(html)
        logger.info("Tear sheet saved to %s", path)

    def save_png(self, directory: Path | str) -> list[Path]:
        """Save each plot as a separate PNG file."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        plots = [
            ("metrics", self.metrics_table()),
            ("equity_curve", self.equity_curve_plot()),
            ("drawdown", self.drawdown_plot()),
            ("monthly_returns", self.monthly_returns_heatmap()),
        ]

        paths: list[Path] = []
        for name, fig in plots:
            p = directory / f"{name}.png"
            fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            paths.append(p)

        return paths
