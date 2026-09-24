"""Core Financial Engine: sector-agnostic money operations.

Must not import Agriculture, Dairy, or farm field catalogues.
"""

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import (
    round_margin_pct,
    round_margin_ratio,
    round_money,
)
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct

__all__ = [
    "net_profit",
    "profit_margin",
    "profit_margin_pct",
    "round_margin_pct",
    "round_margin_ratio",
    "round_money",
    "sum_amounts",
]
