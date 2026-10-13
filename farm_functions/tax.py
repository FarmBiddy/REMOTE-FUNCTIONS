"""Irish tax estimates (ADR-0053).

``tax.stock_relief``: picks the relief the taxpayer is entitled to for the
period (young trained farmer in their 4 years, registered farm partnership,
else general) and applies it to the trading stock increase, using the same
opening / closing valuations ``pl.net`` takes.

``tax.capital_allowances``: allowances for one tax year on the
``assets.schedule`` register, and the bridge from accounting profit to taxable
profit (depreciation added back, allowances deducted).

``tax.estimate``: income tax (joint assessment when married), USC and PRSI for
individuals, or corporation tax for companies, on taxable profit after both,
with the stock relief caps measured as tax saved.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from farm_functions.core.ratios import per_unit
from farm_functions.core.rounding import round_margin_pct, round_money
from farm_functions.ie import capital_allowances as ca
from farm_functions.ie.rules import Rule, rule_at
from farm_functions.ie.taxes import LAST_TAX_YEAR, RULES, banded, year_rules
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


def _usc(v: dict[str, float], income: float, non_paye: float) -> float:
    if income <= v["usc_exemption_threshold"]:
        return 0.0
    ceilings = (v["usc_band_low_ceiling"], v["usc_band_2pct_ceiling"], v["usc_band_middle_ceiling"])
    usc = banded(income, ceilings, (0.5, 2.0, v["usc_rate_middle"], 8.0))
    return usc + max(non_paye - v["usc_surcharge_threshold"], 0.0) * 3 / 100


def _individual(v: dict[str, float], farm_profit: float, other_income: float, married: bool, spouse: float) -> dict:
    """Joint assessment when married: one band and credit set for the couple;
    USC and PRSI per person. Farm losses count as nil (no loss relief)."""
    earned = max(farm_profit, 0.0)
    farmer = earned + other_income
    if married:
        band = v["it_band_married_one_income"] + min(v["it_band_married_second_income_max"], farmer, spouse)
        personal = v["it_credit_personal_married"]
    else:
        band, personal = v["it_band_single"], v["it_credit_personal_single"]
    total = farmer + spouse
    at_standard = min(total, band)
    gross = banded(total, (band,), (v["it_rate_standard"], v["it_rate_higher"]))
    credits = (
        personal
        + min(v["it_credit_earned_income"], earned * v["it_rate_standard"] / 100)
        + min(v["it_credit_employee"], spouse * v["it_rate_standard"] / 100)
    )
    prsi_farmer = 0.0 if farmer < v["prsi_s_threshold"] else max(farmer * v["prsi_s_rate"] / 100, v["prsi_s_minimum"])
    prsi_spouse = 0.0 if spouse / 52 <= v["prsi_a_weekly_exemption"] else spouse * v["prsi_a_rate"] / 100
    return {
        "income": {"farmer": farmer, "spouse": spouse, "total": total},
        "income_tax": {
            "standard_rate_band": band,
            "at_standard_rate": at_standard,
            "at_higher_rate": total - at_standard,
            "gross": gross,
            "credits": credits,
            "net": max(gross - credits, 0.0),
        },
        "usc": {"farmer": _usc(v, farmer, farmer), "spouse": _usc(v, spouse, 0.0)},
        "prsi": {"farmer": prsi_farmer, "spouse": prsi_spouse},
    }


def _it_usc(person: dict) -> float:
    return person["income_tax"]["net"] + person["usc"]["farmer"] + person["usc"]["spouse"]


def _rounded(lines: dict[str, float]) -> dict[str, float]:
    out = {k: round_money(x) for k, x in lines.items()}
    return {**out, "total": round_money(sum(out.values()))}


def tax_estimate(*, tax_year: int, **inputs: Any) -> dict[str, Any]:
    """``tax.estimate``: tax for one year on taxable farming profit (after capital
    allowances and stock relief), applying the stock relief caps on tax value."""
    return estimate_with_rules(year_rules(tax_year), tax_year=tax_year, **inputs)


def estimate_with_rules(
    rules: dict[str, Rule],
    *,
    business_type: str,
    tax_year: int,
    taxable_profit: float,
    other_income: float = 0.0,
    marital_status: str = "single",
    spouse_paye_income: float = 0.0,
    stock_relief: float = 0.0,
    stock_relief_regime: str = "general",
    state_aid_used: float = 0.0,
) -> dict[str, Any]:
    v = {k: r.value for k, r in rules.items()}
    used: list[str]
    income_tax = usc = prsi = corporation = cap = None
    if business_type == "company":
        used = ["ct_rate_trading", "ct_rate_non_trading"]
        corporation = _rounded({
            "trading": max(taxable_profit, 0.0) * v["ct_rate_trading"] / 100,
            "non_trading": other_income * v["ct_rate_non_trading"] / 100,
        })
        income = {"farm_profit": taxable_profit, "other_income": other_income, "spouse_paye_income": 0.0}
        total_tax = corporation["total"]
    else:
        used = [k for k in RULES if k.startswith(("it_", "usc_", "prsi_"))]
        married = marital_status == "married"
        person = _individual(v, taxable_profit, other_income, married, spouse_paye_income)
        clawback = 0.0
        if stock_relief_regime != "general" and stock_relief > 0:
            without = _individual(v, taxable_profit + stock_relief, other_income, married, spouse_paye_income)
            tax_value = _it_usc(without) - _it_usc(person)
            if stock_relief_regime == "young_trained_farmer":
                used += ["stock_relief_ytf_cap", "state_aid_young_farmer_lifetime"]
                limit = min(v["stock_relief_ytf_cap"], max(v["state_aid_young_farmer_lifetime"] - state_aid_used, 0.0))
            else:
                used.append("stock_relief_rfp_de_minimis")
                limit = max(v["stock_relief_rfp_de_minimis"] - state_aid_used, 0.0)
            clawback = max(tax_value - limit, 0.0)
            cap = {
                "regime": stock_relief_regime,
                "relief": round_money(stock_relief),
                "tax_value": round_money(tax_value),
                "cap": round_money(limit),
                "clawback": round_money(clawback),
            }
        it = person["income_tax"]
        income_tax = {k: round_money(x) for k, x in it.items()}
        usc = _rounded(person["usc"])
        prsi = _rounded(person["prsi"])
        income = {"farm_profit": taxable_profit, "other_income": other_income, "spouse_paye_income": spouse_paye_income}
        total_tax = round_money(income_tax["net"] + usc["total"] + prsi["total"] + round_money(clawback))
    income = {k: round_money(x) for k, x in income.items()}
    income["total"] = round_money(max(income["farm_profit"], 0.0) + income["other_income"] + income["spouse_paye_income"])
    rate = per_unit(total_tax, income["total"])
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "business_type": business_type,
        "tax_year": tax_year,
        "assessment": "company" if business_type == "company" else ("joint" if marital_status == "married" else "single"),
        "income": income,
        "income_tax": income_tax,
        "usc": usc,
        "prsi": prsi,
        "corporation_tax": corporation,
        "stock_relief_cap": cap,
        "total_tax": total_tax,
        "effective_rate_pct": None if rate is None else round_margin_pct(rate * 100),
        "rules_applied": [rules[k].as_dict() for k in used],
    }


def projected_tax(
    profile: dict[str, Any],
    history: list[float],
    *,
    tax_year: int,
    period_end_month: int,
    operating_profit: float,
    livestock_increase: float,
    register: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tax for one ``plan.projection`` year (ADR-0053 phase 5).

    ``history`` holds farming profits before capital allowances (oldest first,
    seeded with the Platform's prior years) and gains this year's. Years after
    the last tax year with rules use that year's rules, labelled
    ``latest_held_constant``: a planning assumption, not a forecast of Budgets.
    """
    basis_year = min(tax_year, LAST_TAX_YEAR)
    company = profile["business_type"] == "company"
    allowances = (
        tax_capital_allowances(tax_year=tax_year, assets=register, period_end_month=period_end_month)["total"]["allowance"]
        if register
        else 0.0
    )
    profit = operating_profit + livestock_increase
    regime, table = (
        ("general", GENERAL)
        if company
        else stock_relief_regime(tax_year, profile["registered_partnership"], profile["young_trained_farmer_first_year"])
    )
    rule = rule_at(table, date(basis_year, period_end_month, 1))
    relief = stock_relief(livestock_increase, rule.value, profit - allowances)
    before_allowances = profit - relief
    history.append(before_allowances)
    averaged, averaging = before_allowances, "off"
    if profile["income_averaging"]:
        if len(history) >= 5:
            averaged, averaging = sum(history[-5:]) / 5, "applied"
        else:
            averaging = "insufficient_history"
    estimate = estimate_with_rules(
        year_rules(basis_year),
        business_type=profile["business_type"],
        tax_year=tax_year,
        taxable_profit=averaged - allowances,
        other_income=profile["other_income"],
        marital_status=profile["marital_status"],
        spouse_paye_income=profile["spouse_paye_income"],
        stock_relief=relief,
        stock_relief_regime=regime,
        state_aid_used=profile["state_aid_used"],
    )
    return {
        "tax_year": tax_year,
        "rules_basis": "in_force" if basis_year == tax_year else "latest_held_constant",
        "rules_status": (
            "announced" if any(r["status"] == "announced" for r in estimate["rules_applied"]) else "enacted"
        ),
        "profit_before_allowances": round_money(profit),
        "livestock_increase": round_money(livestock_increase),
        "stock_relief_regime": regime,
        "stock_relief": round_money(relief),
        "capital_allowances": round_money(allowances),
        "averaging": averaging,
        "averaged_profit": round_money(averaged),
        "assessable_profit": round_money(averaged - allowances),
        "total_tax": estimate["total_tax"],
        "effective_rate_pct": estimate["effective_rate_pct"],
    }


__all__ = [
    "estimate_with_rules",
    "projected_tax",
    "resolve_allowance",
    "stock_relief_regime",
    "tax_capital_allowances",
    "tax_estimate",
    "tax_stock_relief",
]
