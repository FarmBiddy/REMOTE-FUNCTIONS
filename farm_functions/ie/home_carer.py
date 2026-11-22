"""Irish home carer tax credit (TCA s.466A; ADR-0055).

For a jointly assessed couple where one spouse cares for a dependant at home
(the Platform confirms eligibility). Full credit while the carer's income is
at most the limit, then reduced by half the excess. It cannot be combined with
the second-earner band increase: Revenue gives whichever is better. Values:
``docs/ie-rules.md`` §2A (TDM 15-01-29). Kept apart from the yearly tax table:
2027's income limit is not confirmed, and a missing rule here must not stop a
2027 estimate without a home carer claim.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

CREDIT: tuple[Rule, ...] = (
    Rule("home_carer_credit", 1_800.0, date(2024, 1, 1), date(2024, 12, 31), "TCA s.466A; TDM 15-01-29", "enacted"),
    Rule("home_carer_credit", 1_950.0, date(2025, 1, 1), date(2026, 12, 31), "TCA s.466A; TDM 15-01-29", "enacted"),
)
INCOME_LIMIT: tuple[Rule, ...] = (
    Rule("home_carer_income_limit", 7_200.0, date(2024, 1, 1), date(2026, 12, 31), "TCA s.466A(3); TDM 15-01-29", "enacted"),
)


def home_carer_rules(tax_year: int) -> tuple[Rule, Rule] | None:
    credit, limit = (rule_at(t, date(tax_year, 1, 1)) for t in (CREDIT, INCOME_LIMIT))
    return None if credit is None or limit is None else (credit, limit)


def home_carer_credit(credit: float, limit: float, carer_income: float) -> float:
    """The credit after the taper: less half of the carer's income above the limit."""
    return max(credit - max(carer_income - limit, 0.0) / 2, 0.0)


__all__ = ["CREDIT", "INCOME_LIMIT", "home_carer_credit", "home_carer_rules"]
