"""Irish tax estimates (ADR-0053). ``tax.stock_relief``: farm stock relief.

Application layer: picks the relief the taxpayer is entitled to for the period
(young trained farmer in their 4 years, registered farm partnership, else
general) and applies it to the trading stock increase. Stock values are the
same opening / closing livestock and stock valuations ``pl.net`` takes.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from farm_functions.core.rounding import round_money
from farm_functions.ie.rules import Rule, rule_at
from farm_functions.ie.stock_relief import (
    GENERAL,
    REGISTERED_PARTNERSHIP,
    YOUNG_TRAINED_FARMER,
    YOUNG_TRAINED_FARMER_YEARS,
    stock_relief,
)

# Caps measured as tax saved: applied once tax is estimated (ADR-0053 phase 4).
_CAPS = {
    "young_trained_farmer": ["stock_relief_ytf_cap", "state_aid_young_farmer_lifetime"],
    "registered_partnership": ["stock_relief_rfp_de_minimis"],
    "general": [],
}


def stock_relief_regime(
    period_end_year: int,
    registered_partnership: bool,
    young_trained_farmer_first_year: int | None,
) -> tuple[str, tuple[Rule, ...]]:
    first = young_trained_farmer_first_year
    if first is not None and first <= period_end_year < first + YOUNG_TRAINED_FARMER_YEARS:
        return "young_trained_farmer", YOUNG_TRAINED_FARMER
    if registered_partnership:
        return "registered_partnership", REGISTERED_PARTNERSHIP
    return "general", GENERAL


def tax_stock_relief(
    *,
    business_type: str,
    period_end_year: int,
    period_end_month: int = 12,
    trading_profit: float,
    livestock_opening_value: float = 0.0,
    livestock_closing_value: float = 0.0,
    stock_opening_value: float = 0.0,
    stock_closing_value: float = 0.0,
    registered_partnership: bool = False,
    young_trained_farmer_first_year: int | None = None,
) -> dict[str, Any]:
    regime, rules = stock_relief_regime(period_end_year, registered_partnership, young_trained_farmer_first_year)
    rule = rule_at(rules, date(period_end_year, period_end_month, 1))
    opening = livestock_opening_value + stock_opening_value
    closing = livestock_closing_value + stock_closing_value
    increase = closing - opening
    uncapped = max(increase, 0.0) * rule.value / 100
    relief = stock_relief(increase, rule.value, trading_profit)
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "business_type": business_type,
        "period_end": {"kind": "month", "year": period_end_year, "month": period_end_month},
        "regime": regime,
        "opening_stock": round_money(opening),
        "closing_stock": round_money(closing),
        "stock_increase": round_money(increase),
        "rate_pct": rule.value,
        "relief_before_profit_limit": round_money(uncapped),
        "trading_profit": round_money(trading_profit),
        "relief": round_money(relief),
        "profit_after_relief": round_money(trading_profit - relief),
        "restricted_by_profit": relief < uncapped,
        # s.666(3): in a claim year, losses and capital allowances brought forward stop there.
        "losses_forward_restricted": relief > 0,
        "caps_not_applied": _CAPS[regime],
        "rules_applied": [rule.as_dict()],
    }


__all__ = ["stock_relief_regime", "tax_stock_relief"]
