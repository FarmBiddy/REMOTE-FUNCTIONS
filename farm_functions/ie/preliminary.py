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


# Month of the statutory pay date (31 October).
PAY_MONTH = 10


def pay_year(first_month: int, last_month: int) -> int:
    """Calendar year of the October inside a 12-month span (month indexes
    ``year * 12 + month - 1``): the tax year whose preliminary tax, with the
    year before's balance, is paid in that span."""
    october = next(m for m in range(first_month, last_month + 1) if m % 12 == PAY_MONTH - 1)
    return october // 12


def preliminary_amount(basis: str, rate_pct: float, liabilities: dict[int, float], tax_year: int) -> float:
    """Preliminary tax for ``tax_year`` on a basis: 90% of that year's tax, or
    100% of the year before's (``liabilities`` by tax year)."""
    base_year = tax_year if basis == "current_90" else tax_year - 1
    return liabilities[base_year] * rate_pct / 100


def history_needed(first_month: int, last_month: int) -> dict[int, bool]:
    """Tax years before a plan whose tax the first pay date needs, each with
    whether its preliminary tax already paid is needed too. The year before the
    first pay year always (its balance is paid then); the first pay year itself
    when its accounts end before the plan's first tax year (e.g. a March year end)."""
    first_pay, first_tax_year = pay_year(first_month, last_month), last_month // 12
    needed = {first_pay - 1: True}
    if first_pay < first_tax_year:
        needed[first_pay] = False
    return needed


def instalments(total_cents: int, months: int) -> list[int]:
    """Equal monthly amounts in cents, the remainder in the last month."""
    each = total_cents // months
    return [each] * (months - 1) + [total_cents - each * (months - 1)]


__all__ = [
    "BASES",
    "DIRECT_DEBIT_BASIS",
    "DIRECT_DEBIT_DAY",
    "PAY_MONTH",
    "ROS_PAY_AND_FILE",
    "SAFE_HARBOUR",
    "STATUTORY_DAY_OF_OCTOBER",
    "history_needed",
    "instalments",
    "pay_year",
    "preliminary_amount",
    "safe_harbour_rule",
]
