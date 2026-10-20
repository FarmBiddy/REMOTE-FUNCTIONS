"""Irish farm stock relief (TCA s.665–667C; ADR-0053).

Relief = rate × increase in trading stock (livestock, crops, feed, fertiliser)
over the accounting period, as a trading deduction that can never create or
increase a loss. Rates: ``docs/ie-rules.md`` §4. ``from`` dates mark the start
of the researched window (2024), not when each relief began.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule

_END = date(2027, 12, 31)

GENERAL: tuple[Rule, ...] = (
    Rule("stock_relief_general", 25.0, date(2024, 1, 1), _END, "TCA s.666", "enacted"),
)
YOUNG_TRAINED_FARMER: tuple[Rule, ...] = (
    Rule("stock_relief_ytf", 100.0, date(2024, 1, 1), _END, "TCA s.667B", "enacted"),
)
REGISTERED_PARTNERSHIP: tuple[Rule, ...] = (
    Rule("stock_relief_rfp", 50.0, date(2024, 1, 1), _END, "TCA s.667C", "enacted"),
)
# Year the farmer first qualifies plus the next 3 tax years (s.667B).
YOUNG_TRAINED_FARMER_YEARS = 4


def stock_relief(stock_increase: float, rate_pct: float, profit_before_relief: float) -> float:
    """Relief on a stock increase, limited so it never creates or increases a loss."""
    relief = max(float(stock_increase), 0.0) * float(rate_pct) / 100
    return min(relief, max(float(profit_before_relief), 0.0))


__all__ = [
    "GENERAL",
    "REGISTERED_PARTNERSHIP",
    "YOUNG_TRAINED_FARMER",
    "YOUNG_TRAINED_FARMER_YEARS",
    "stock_relief",
]
