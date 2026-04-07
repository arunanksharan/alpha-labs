"""Portfolio optimisation module.

Exports:
    PortfolioOptimizer -- unified optimisation interface.
    PortfolioResult    -- dataclass holding optimisation output.
"""

from portfolio.optimization.optimizer import PortfolioOptimizer, PortfolioResult

__all__ = ["PortfolioOptimizer", "PortfolioResult"]
