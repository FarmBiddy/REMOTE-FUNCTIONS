"""Irish tax estimates (ADR-0053).

``tax.stock_relief``: picks the relief the taxpayer is entitled to for the
period (young trained farmer in their 4 years, registered farm partnership,
else general) and applies it to the trading stock increase, using the same
opening / closing valuations ``pl.net`` takes.

``tax.capital_allowances``: allowances for one tax year on the
``assets.schedule`` register, and the bridge from accounting profit to taxable
profit (depreciation added back, allowances deducted).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from farm_functions.core.rounding import round_money
from farm_functions.ie import capital_allowances as ca
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


def resolve_allowance(kind: str, year: int, month: int) -> tuple[str, Rule | None]:
    """Allowance type actually given for a spend date, falling back from an
    accelerated scheme outside its window. ``none`` has no rule."""
    if kind == "none":
        return kind, None
    rule = rule_at(ca.RULES[kind], date(year, month, 1))
    if rule is None and kind in ca.FALLBACK:
        kind = ca.FALLBACK[kind]
        rule = rule_at(ca.RULES[kind], date(year, month, 1))
    return kind, rule


def tax_capital_allowances(
    *,
    tax_year: int,
    assets: list[dict[str, Any]],
    period_end_month: int = 12,
    accounting_profit: float | None = None,
    depreciation: float = 0.0,
) -> dict[str, Any]:
    """``tax.capital_allowances``: allowances for one tax year per asset (input order)."""
    rows, rules, caps = [], {}, set()
    for asset in assets:
        requested = asset.get("tax_allowance") or ca.DEFAULT_FOR_CATEGORY[asset["category"]]
        applied, rule = resolve_allowance(requested, asset["year"], asset["month"])
        spend_year = asset["year"] + (asset["month"] > period_end_month)
        qualifying = asset["cost"] - asset.get("grant", 0.0)
        opening = allowance = closing = 0.0
        if rule is not None and tax_year >= spend_year:
            opening, allowance, closing = ca.allowance_in_year(qualifying, ca.SCHEDULES[applied], tax_year - spend_year)
            rules[(rule.rule_id, rule.start)] = rule
            if allowance and applied in ca.CAPS:
                caps.add(ca.CAPS[applied])
        rows.append(
            {
                "category": asset["category"],
                "allowance_type": requested,
                "allowance_applied": applied,
                "qualifying_cost": round_money(qualifying),
                "opening_twdv": round_money(opening),
                "allowance": round_money(allowance),
                "closing_twdv": round_money(closing),
            }
        )
    total = round_money(sum(r["allowance"] for r in rows))
    bridge = None
    if accounting_profit is not None:
        bridge = {
            "accounting_profit": round_money(accounting_profit),
            "add_back_depreciation": round_money(depreciation),
            "capital_allowances": total,
            "taxable_profit": round_money(accounting_profit + depreciation - total),
        }
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "tax_year": tax_year,
        "period_end_month": period_end_month,
        "assets": rows,
        "by_type": {
            t: round_money(sum(r["allowance"] for r in rows if r["allowance_applied"] == t)) for t in ca.SCHEDULES
        },
        "total": {
            f: round_money(sum(r[f] for r in rows)) for f in ("opening_twdv", "allowance", "closing_twdv")
        },
        "profit_bridge": bridge,
        "caps_not_applied": sorted(caps),
        "rules_applied": [rules[k].as_dict() for k in sorted(rules)],
    }


__all__ = ["resolve_allowance", "stock_relief_regime", "tax_capital_allowances", "tax_stock_relief"]
