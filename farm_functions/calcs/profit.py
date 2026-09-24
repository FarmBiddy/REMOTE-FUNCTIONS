"""Compatibility re-exports. Canonical implementation: ``farm_functions.core.surplus``.

Public calculation ID ``profit.net`` is unchanged.
"""

from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct

__all__ = ["net_profit", "profit_margin", "profit_margin_pct"]
