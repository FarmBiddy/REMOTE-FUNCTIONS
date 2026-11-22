"""Irish pension contribution relief for the self-employed (ADR-0055).

Retirement annuity / PRSA contributions (TCA s.787, s.787E) are relieved
against income tax only, at the individual's marginal rate (not USC or PRSI),
up to an age-related % of net relevant earnings, with earnings capped at
€115,000 (s.790A). Age is the age reached in the tax year. Unrelieved
contributions carry forward. Sources: Revenue Pensions Manual Ch. 3, 21, 24;
``docs/ie-rules.md`` §6C. ``from`` dates mark the start of the researched
window (2024), not when each limit began.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

_START, _END = date(2024, 1, 1), date(2027, 12, 31)
_REF = "TCA s.787 (Revenue Pensions Manual Ch. 3)"

# (age from, rule): the % of net relevant earnings that can be relieved.
AGE_BANDS: tuple[tuple[int, tuple[Rule, ...]], ...] = tuple(
    (age, (Rule(f"pension_pct_from_age_{age}", pct, _START, _END, _REF, "enacted"),))
    for age, pct in ((0, 15.0), (30, 20.0), (40, 25.0), (50, 30.0), (55, 35.0), (60, 40.0))
)
EARNINGS_CAP: tuple[Rule, ...] = (
    Rule("pension_earnings_cap", 115_000.0, _START, _END, "TCA s.790A", "enacted"),
)


def age_band_rule(age: int, tax_year: int) -> Rule | None:
    """The % rule for the age reached in the tax year."""
    rules = next(r for a, r in reversed(AGE_BANDS) if age >= a)
    return rule_at(rules, date(tax_year, 1, 1))


def earnings_cap_rule(tax_year: int) -> Rule | None:
    return rule_at(EARNINGS_CAP, date(tax_year, 1, 1))


def relief(contributions: float, net_relevant_earnings: float, pct: float, cap: float) -> float:
    """Contributions relieved this year: at most pct × earnings (capped, never below 0)."""
    return min(contributions, pct / 100 * min(max(net_relevant_earnings, 0.0), cap))


__all__ = ["AGE_BANDS", "EARNINGS_CAP", "age_band_rule", "earnings_cap_rule", "relief"]
