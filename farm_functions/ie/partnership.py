"""Irish farm partnerships (TCA s.667C, s.667D, Part 43; ADR-0053).

A partnership is transparent: profit is split by the profit-sharing ratio and
each partner is taxed on their share. The succession farm partnership credit
is fixed by the year the partnership is registered and runs for that year and
the next 4, split by profit share. Rules: ``docs/ie-rules.md`` §7.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule

SUCCESSION_CREDIT: tuple[Rule, ...] = (
    Rule("sfp_credit", 5_000.0, date(2017, 5, 31), date(2026, 12, 31), "TCA s.667D", "enacted"),
    Rule("sfp_credit", 10_000.0, date(2027, 1, 1), None, "Finance (No. 2) Bill 2026 s.23", "announced"),
)
SUCCESSION_CREDIT_YEARS = 5
SUCCESSOR_AGE_LIMIT = 40  # no credit in a year the successor is 40 or over on 1 January
MIN_SUCCESSOR_SHARE_PCT = 20.0


def succession_credit(credit: float, share_pct: float, assessable_profit: float) -> float:
    """Partner's credit: their share of the credit, at most their assessable profit."""
    return min(float(credit) * float(share_pct) / 100, max(float(assessable_profit), 0.0))


__all__ = [
    "MIN_SUCCESSOR_SHARE_PCT",
    "SUCCESSION_CREDIT",
    "SUCCESSION_CREDIT_YEARS",
    "SUCCESSOR_AGE_LIMIT",
    "succession_credit",
]
