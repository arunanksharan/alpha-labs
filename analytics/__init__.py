"""Analytics module for quantitative research.

Exports core returns/risk metrics and statistical testing functions.
"""

from analytics.returns import (
    compute_alpha,
    compute_beta,
    compute_calmar,
    compute_correlation_matrix,
    compute_cumulative_returns,
    compute_cvar,
    compute_drawdown,
    compute_information_ratio,
    compute_max_drawdown,
    compute_returns,
    compute_rolling_correlation,
    compute_sharpe,
    compute_sortino,
    compute_var,
    compute_volatility,
)
from analytics.filters import CUSUMFilter, EventFilter
from analytics.structural_breaks import StructuralBreakDetector
from analytics.statistics import (
    adf_test,
    engle_granger_cointegration,
    half_life_mean_reversion,
    hurst_exponent,
    jarque_bera_test,
    johansen_cointegration,
    ks_test,
    kpss_test,
    ljung_box_test,
    rolling_adf,
)

__all__ = [
    "compute_returns",
    "compute_cumulative_returns",
    "compute_drawdown",
    "compute_volatility",
    "compute_sharpe",
    "compute_sortino",
    "compute_calmar",
    "compute_max_drawdown",
    "compute_var",
    "compute_cvar",
    "compute_correlation_matrix",
    "compute_rolling_correlation",
    "compute_beta",
    "compute_alpha",
    "compute_information_ratio",
    "adf_test",
    "kpss_test",
    "hurst_exponent",
    "jarque_bera_test",
    "ljung_box_test",
    "engle_granger_cointegration",
    "johansen_cointegration",
    "ks_test",
    "half_life_mean_reversion",
    "rolling_adf",
    "EventFilter",
    "CUSUMFilter",
    "StructuralBreakDetector",
]
