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


# Step-out (s.657(6A), from 2016): one year on actual profit; the income tax
# deferred is paid in equal yearly instalments, the first on the return date for
# the year after the step-out year (31 October two years on); no step-out if one
# was made in the previous years of the gap.
STEP_OUT_INSTALMENTS: tuple[Rule, ...] = (
    Rule("averaging_step_out_instalments", 4, date(2024, 1, 1), date(2027, 12, 31), "TCA s.657(6A)(b)-(c)", "enacted"),
)
STEP_OUT_GAP_YEARS: tuple[Rule, ...] = (
    Rule("averaging_step_out_gap_years", 4, date(2024, 1, 1), date(2027, 12, 31), "TCA s.657(6A)(d)", "enacted"),
)


def step_out_rules(tax_year: int) -> tuple[Rule, Rule] | None:
    on = date(tax_year, 1, 1)
    count, gap = rule_at(STEP_OUT_INSTALMENTS, on), rule_at(STEP_OUT_GAP_YEARS, on)
    return None if count is None or gap is None else (count, gap)


def step_out_due_years(tax_year: int, instalments: int) -> list[int]:
    """Years whose 31 October each instalment is due: from two years after the step-out year."""
    return [tax_year + 2 + k for k in range(instalments)]


def averaging_rule(tax_year: int) -> Rule | None:
    """The averaging period in force for the tax year, or None."""
    return rule_at(AVERAGING_YEARS, date(tax_year, 1, 1))


def averaged_profit(profits: list[float], years: int) -> float:
    """Average of the last ``years`` farming profits (oldest first, before
    capital allowances). The caller checks there are enough years."""
    window = profits[-years:]
    return sum(window) / years


__all__ = [
    "AVERAGING_YEARS",
    "STEP_OUT_GAP_YEARS",
    "STEP_OUT_INSTALMENTS",
    "averaged_profit",
    "averaging_rule",
    "step_out_due_years",
    "step_out_rules",
]
