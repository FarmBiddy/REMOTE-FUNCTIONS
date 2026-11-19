"""Irish preliminary income tax and pay dates (TCA Part 41A; ADR-0055).

Preliminary tax for a tax year and the balance of the year before are due on
31 October of the tax year (s.959AO). No interest if the preliminary tax paid
is at least the least of: 90% of this year's tax, 100% of last year's, or
(direct debit only, and not if that year's tax was nil) 105% of the year
before last (s.959AO(3)(b), s.959AP). Filing and paying through ROS moves the
date to the one Revenue announces each year (administrative practice).
Values and sources: ``docs/ie-rules.md`` §6A. ``from`` dates mark the start of
the researched window (2024), not when each rule began.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

_START, _END = date(2024, 1, 1), date(2027, 12, 31)

SAFE_HARBOUR: dict[str, tuple[Rule, ...]] = {
    "current_90": (Rule("prelim_current_year_pct", 90.0, _START, _END, "TCA s.959AO(3)(b)(i)", "enacted"),),
    "prior_100": (Rule("prelim_prior_year_pct", 100.0, _START, _END, "TCA s.959AO(3)(b)(ii)", "enacted"),),
    "pre_preceding_105_dd": (
        Rule("prelim_pre_preceding_year_dd_pct", 105.0, _START, _END, "TCA s.959AO(3)(b)(iii), s.959AP", "enacted"),
    ),
}
BASES = tuple(SAFE_HARBOUR)
DIRECT_DEBIT_BASIS = "pre_preceding_105_dd"

# Statutory pay date: day of October of the tax year (s.959AO(1), (2)(a)).
STATUTORY_DAY_OF_OCTOBER = 31

# ROS pay-and-file date by tax year of the preliminary tax (return of the year
# before). Revenue announces each one; a year not listed has only 31 October.
ROS_PAY_AND_FILE: dict[int, tuple[date, str]] = {
    2025: (date(2025, 11, 19), "Revenue eBrief 088/25"),
    2026: (date(2026, 11, 18), "Revenue eBrief 034/26"),
}

# Direct debit instalments are taken on this day of each month (Revenue DD guidelines).
DIRECT_DEBIT_DAY = 9


def safe_harbour_rule(basis: str, tax_year: int) -> Rule | None:
    return rule_at(SAFE_HARBOUR[basis], date(tax_year, 1, 1))


def instalments(total_cents: int, months: int) -> list[int]:
    """Equal monthly amounts in cents, the remainder in the last month."""
    each = total_cents // months
    return [each] * (months - 1) + [total_cents - each * (months - 1)]


__all__ = [
    "BASES",
    "DIRECT_DEBIT_BASIS",
    "DIRECT_DEBIT_DAY",
    "ROS_PAY_AND_FILE",
    "SAFE_HARBOUR",
    "STATUTORY_DAY_OF_OCTOBER",
    "instalments",
    "safe_harbour_rule",
]
