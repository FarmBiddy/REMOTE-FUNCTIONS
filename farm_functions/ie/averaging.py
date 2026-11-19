"""Irish income averaging for farmers (TCA s.657; ADR-0053, ADR-0055).

Assessable farming profit = average of this year and the previous years of the
averaging period, each before capital allowances and balancing charges; the
year's own allowances are then deducted. Period length: ``docs/ie-rules.md``
§6. ``from`` dates mark the start of the researched window (2024), not when
averaging began.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

AVERAGING_YEARS: tuple[Rule, ...] = (
    Rule("income_averaging_years", 5, date(2024, 1, 1), date(2027, 12, 31), "TCA s.657", "enacted"),
)


def averaging_rule(tax_year: int) -> Rule | None:
    """The averaging period in force for the tax year, or None."""
    return rule_at(AVERAGING_YEARS, date(tax_year, 1, 1))


def averaged_profit(profits: list[float], years: int) -> float:
    """Average of the last ``years`` farming profits (oldest first, before
    capital allowances). The caller checks there are enough years."""
    window = profits[-years:]
    return sum(window) / years


__all__ = ["AVERAGING_YEARS", "averaged_profit", "averaging_rule"]
