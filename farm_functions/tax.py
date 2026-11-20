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
from farm_functions.ie import home_carer as carer
from farm_functions.ie import pensions
from farm_functions.ie import preliminary as prelim
from farm_functions.ie.averaging import (
    averaged_profit,
    averaging_rule,
    exit_top_ups,
    step_out_due_years,
    step_out_rules,
)
from farm_functions.ie.losses import PRSI_TREATMENT as LOSS_PRSI_TREATMENT
from farm_functions.ie.losses import apply_losses
from farm_functions.ie.partnership import (
    SUCCESSION_CREDIT,
    SUCCESSION_CREDIT_YEARS,
    SUCCESSOR_AGE_LIMIT,
    succession_credit,
)
from farm_functions.ie.rules import Rule, rule_at
from farm_functions.ie.taxes import LAST_TAX_YEAR, RULES, banded, year_rules
from farm_functions.ie.vat import FLAT_RATE_ADDITION, flat_rate_addition
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


def resolve_allowance(kind: str, year: int, month: int, category: str) -> tuple[str, Rule | None]:
    """Allowance type actually given for a spend date, falling back from an
    accelerated scheme outside its window. ``none`` has no rule."""
    if kind == "none":
        return kind, None
    rule = rule_at(ca.RULES[kind], date(year, month, 1))
    normal = ca.fallback(kind, category)
    if rule is None and normal:
        kind, rule = normal, rule_at(ca.RULES[normal], date(year, month, 1))
    return kind, rule


def tax_capital_allowances(
    *,
    tax_year: int,
    assets: list[dict[str, Any]],
    period_end_month: int = 12,
    accounting_profit: float | None = None,
    depreciation: float = 0.0,
) -> dict[str, Any]:
    """``tax.capital_allowances``: allowances for one tax year per asset (input order).
    The flat-rate VAT addition is already in ``accounting_profit`` (a P&L line, ADR-0055)."""
    rows, rules, caps = [], {}, set()
    for asset in assets:
        requested = asset.get("tax_allowance") or ca.DEFAULT_FOR_CATEGORY[asset["category"]]
        applied, rule = resolve_allowance(requested, asset["year"], asset["month"], asset["category"])
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


def _individual(
    v: dict[str, float],
    farm_profit: float,
    other_income: float,
    married: bool,
    spouse: float,
    extra_credit: float = 0.0,
    paye: float = 0.0,
    it_deduction: float = 0.0,
    home_carer_credit: float = 0.0,
    spouse_self_employed: float = 0.0,
    spouse_farm_wages: float = 0.0,
) -> dict:
    """Joint assessment when married: one band and credit set for the couple;
    USC and PRSI per person. Farm losses count as nil (no loss relief).
    ``it_deduction`` (pension relief) reduces income for income tax only.
    ``home_carer_credit`` (already tapered) replaces the second-earner band
    increase when that gives less tax, as Revenue applies it (s.466A).
    The spouse's income (ADR-0055): ``spouse`` PAYE pay (employee credit, Class
    A), ``spouse_self_employed`` their own trade (earned income credit, Class S,
    non-PAYE for USC) and ``spouse_farm_wages`` paid by the farmer (earned income
    credit, no employee credit, PAYE for USC, no PRSI: excepted employment)."""
    earned = max(farm_profit, 0.0)
    farmer = earned + other_income
    spouse_paye, spouse = spouse, spouse + spouse_self_employed + spouse_farm_wages
    if married:
        one_income = v["it_band_married_one_income"]
        band = one_income + min(v["it_band_married_second_income_max"], farmer, spouse)
        personal = v["it_credit_personal_married"]
    else:
        band, personal = v["it_band_single"], v["it_credit_personal_single"]
    total = farmer + spouse
    it_income = max(total - it_deduction, 0.0)
    # Employee and earned income credits share one cap per person (s.472AB).
    spouse_credits = min(
        v["it_credit_employee"],
        min(v["it_credit_employee"], spouse_paye * v["it_rate_standard"] / 100)
        + min(v["it_credit_earned_income"], (spouse_self_employed + spouse_farm_wages) * v["it_rate_standard"] / 100),
    )
    credits = (
        personal
        + min(v["it_credit_earned_income"], earned * v["it_rate_standard"] / 100)
        + spouse_credits
        + extra_credit
    )

    def income_tax(band: float, credits: float) -> dict[str, float]:
        at_standard = min(it_income, band)
        gross = banded(it_income, (band,), (v["it_rate_standard"], v["it_rate_higher"]))
        return {
            "standard_rate_band": band,
            "at_standard_rate": at_standard,
            "at_higher_rate": it_income - at_standard,
            "gross": gross,
            "credits": credits,
            "net": max(gross - credits, 0.0),
        }

    it, home_carer = income_tax(band, credits), None
    if married and home_carer_credit:
        with_credit = income_tax(one_income, credits + home_carer_credit)
        home_carer = "credit" if with_credit["net"] < it["net"] else "band_increase"
        if home_carer == "credit":
            it = with_credit
    prsi_farmer = 0.0 if farmer < v["prsi_s_threshold"] else max(farmer * v["prsi_s_rate"] / 100, v["prsi_s_minimum"])
    prsi_spouse = 0.0 if spouse_paye / 52 <= v["prsi_a_weekly_exemption"] else spouse_paye * v["prsi_a_rate"] / 100
    if spouse_self_employed >= v["prsi_s_threshold"]:
        prsi_spouse += max(spouse_self_employed * v["prsi_s_rate"] / 100, v["prsi_s_minimum"])
    return {
        "income": {"farmer": farmer, "spouse": spouse, "total": total},
        "income_tax": it,
        "home_carer": home_carer,
        "usc": {"farmer": _usc(v, farmer, farmer - paye), "spouse": _usc(v, spouse, spouse_self_employed)},
        "prsi": {"farmer": prsi_farmer, "spouse": prsi_spouse},
    }


def _it_usc(person: dict) -> float:
    return person["income_tax"]["net"] + person["usc"]["farmer"] + person["usc"]["spouse"]


def _rounded(lines: dict[str, float]) -> dict[str, float]:
    out = {k: round_money(x) for k, x in lines.items()}
    return {**out, "total": round_money(sum(out.values()))}


def averaging_view(
    tax_year: int, profit_before_allowances: float, prior_farming_profits: list[float], capital_allowances: float
) -> tuple[float, dict[str, Any], Rule]:
    """Income averaging for one year (s.657, ADR-0055): this year's profit before
    capital allowances joins the previous years, the average is assessed and the
    year's own allowances are then deducted. Returns the assessable profit, the
    published view and the rule."""
    rule = averaging_rule(tax_year)
    years = int(rule.value)
    profits = [*prior_farming_profits, profit_before_allowances]
    averaged = averaged_profit(profits, years)
    assessable = averaged - capital_allowances
    view = {
        "years": years,
        "profits_before_allowances": [round_money(p) for p in profits[-years:]],
        "averaged_profit": round_money(averaged),
        "capital_allowances": round_money(capital_allowances),
        "assessable_profit": round_money(assessable),
    }
    return assessable, view, rule


def _estimate_year(
    *,
    tax_year: int,
    taxable_profit: float,
    stock_relief: float = 0.0,
    income_averaging: bool | None = None,
    prior_farming_profits: list[float] | None = None,
    capital_allowances: float | None = None,
    losses_forward: float = 0.0,
    pension_contributions: float = 0.0,
    birth_year: int | None = None,
    home_carer: bool = False,
    **inputs: Any,
) -> dict[str, Any]:
    """``tax.estimate``: tax for one year on taxable farming profit (after capital
    allowances and stock relief), applying the stock relief caps on tax value.
    With income averaging the averaged profit is assessed, and this year's stock
    relief counts a fifth towards its cap (it moves the average by a fifth).
    Individuals' losses brought forward (s.382) then reduce the profit charged;
    pension contributions are relieved against income tax only, up to the age %
    of net relevant earnings (the assessable farm profit, the Engine's reading)."""
    averaging = rule = None
    relief_effect = stock_relief
    if income_averaging:
        taxable_profit, averaging, rule = averaging_view(
            tax_year, taxable_profit + capital_allowances, prior_farming_profits, capital_allowances
        )
        relief_effect = stock_relief / averaging["years"]
    losses = None
    # Without the relief (for its caps): this year's profit + the relief counted, then
    # the same losses and pension limit applied to that higher profit.
    without_profit = taxable_profit + relief_effect
    if inputs["business_type"] != "company":
        taxable_profit, used = apply_losses(taxable_profit, losses_forward, stock_relief > 0)
        losses = {k: round_money(v) for k, v in used.items()} | {"prsi_treatment": LOSS_PRSI_TREATMENT}
        without_profit, _ = apply_losses(without_profit, losses_forward, False)
    pension, pension_rules, without_pension = None, [], 0.0
    if pension_contributions:
        age = tax_year - birth_year
        pct_rule, cap_rule = pensions.age_band_rule(age, tax_year), pensions.earnings_cap_rule(tax_year)
        earnings = max(taxable_profit, 0.0)
        relieved = pensions.relief(pension_contributions, earnings, pct_rule.value, cap_rule.value)
        pension = {
            "contributions": round_money(pension_contributions),
            "age": age,
            "age_pct": pct_rule.value,
            "net_relevant_earnings": round_money(earnings),
            "earnings_basis": "assessable_farm_profit",
            "limit": round_money(pct_rule.value / 100 * min(earnings, cap_rule.value)),
            "relief": round_money(relieved),
            "unrelieved": round_money(pension_contributions - relieved),
        }
        pension_rules = [pct_rule.as_dict(), cap_rule.as_dict()]
        without_pension = pensions.relief(
            pension_contributions, max(without_profit, 0.0), pct_rule.value, cap_rule.value
        )
    carer_credit, carer_rules = 0.0, []
    if home_carer:
        credit_rule, limit_rule = carer.home_carer_rules(tax_year)
        carer_income = sum(
            inputs.get(k, 0.0) for k in ("spouse_paye_income", "spouse_self_employed_income", "spouse_farm_wages")
        )
        carer_credit = carer.home_carer_credit(credit_rule.value, limit_rule.value, carer_income)
        carer_rules = [credit_rule.as_dict(), limit_rule.as_dict()]
    result = estimate_with_rules(
        year_rules(tax_year), tax_year=tax_year, taxable_profit=taxable_profit, stock_relief=relief_effect,
        pension_relief=0.0 if pension is None else pension["relief"], home_carer_credit=carer_credit,
        without_relief_profit=without_profit, without_relief_pension=without_pension, **inputs,
    )
    if home_carer:
        result["home_carer"] = {"credit_after_taper": round_money(carer_credit),
                                "applied": (result["home_carer"] or {}).get("applied", "band_increase")}
        result["rules_applied"] += carer_rules
    if rule is not None:
        result["rules_applied"].append(rule.as_dict())
    result["rules_applied"] += pension_rules
    return {**result, "averaging": averaging, "losses": losses, "pension": pension}


def tax_estimate(
    *, step_out: bool = False, last_step_out_year: int | str | None = None, **inputs: Any
) -> dict[str, Any]:
    """``tax.estimate``. A step-out year (s.657(6A), averaging on) is taxed on
    actual profit; the income tax it saves against the averaged figure is
    deferred and paid in equal yearly instalments from two years on."""
    if not step_out:
        return {**_estimate_year(**inputs), "step_out": None}
    averaged = _estimate_year(**inputs)
    actual = _estimate_year(**{**inputs, "income_averaging": False, "prior_farming_profits": None, "capital_allowances": None})
    tax_year = inputs["tax_year"]
    count_rule, gap_rule = step_out_rules(tax_year)
    on_average, on_actual = averaged["income_tax"]["net"], actual["income_tax"]["net"]
    deferred = round_money(max(on_average - on_actual, 0.0))
    count = int(count_rule.value)
    cents = prelim.instalments(round(deferred * 100), count)
    due = [
        {"due": date(y, 10, prelim.STATUTORY_DAY_OF_OCTOBER).isoformat(), "amount": c / 100}
        for y, c in zip(step_out_due_years(tax_year, count), cents)
    ]
    averaging_rules = [r for r in averaged["rules_applied"] if r["rule_id"] == "income_averaging_years"]
    rules = [*actual["rules_applied"], *averaging_rules, count_rule.as_dict(), gap_rule.as_dict()]
    return {
        **actual,
        # The averaged figure the deferred tax is measured on; this year is taxed on actual.
        "averaging": averaged["averaging"],
        "rules_applied": rules,
        "step_out": {
            "income_tax_on_average": on_average,
            "income_tax_on_actual": on_actual,
            "deferred_income_tax": deferred,
            "instalments": due,
            "last_step_out_year": last_step_out_year,
        },
    }


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
    extra_credit: float = 0.0,
    pension_relief: float = 0.0,
    home_carer_credit: float = 0.0,
    spouse_self_employed_income: float = 0.0,
    spouse_farm_wages: float = 0.0,
    without_relief_profit: float | None = None,
    without_relief_pension: float | None = None,
) -> dict[str, Any]:
    """Tax for one taxpayer on the given rules. The stock relief caps compare
    with the tax had there been no relief: ``without_relief_profit`` /
    ``without_relief_pension`` give that case when losses or the pension limit
    depend on the profit (default: profit + relief, same pension relief)."""
    v = {k: r.value for k, r in rules.items()}
    used: list[str]
    income_tax = usc = prsi = corporation = cap = None
    if business_type == "company":
        used = ["ct_rate_trading", "ct_rate_non_trading"]
        corporation = _rounded({
            "trading": max(taxable_profit, 0.0) * v["ct_rate_trading"] / 100,
            "non_trading": other_income * v["ct_rate_non_trading"] / 100,
        })
        income = {"farm_profit": taxable_profit, "other_income": other_income, "spouse_paye_income": 0.0,
                  "spouse_self_employed_income": 0.0, "spouse_farm_wages": 0.0}
        total_tax = corporation["total"]
    else:
        used = [k for k in RULES if k.startswith(("it_", "usc_", "prsi_"))]
        married = marital_status == "married"
        person = _individual(
            v, taxable_profit, other_income, married, spouse_paye_income, extra_credit,
            it_deduction=pension_relief, home_carer_credit=home_carer_credit,
            spouse_self_employed=spouse_self_employed_income, spouse_farm_wages=spouse_farm_wages,
        )
        clawback = 0.0
        if stock_relief_regime != "general" and stock_relief > 0:
            without = _individual(
                v,
                taxable_profit + stock_relief if without_relief_profit is None else without_relief_profit,
                other_income, married, spouse_paye_income, extra_credit,
                it_deduction=pension_relief if without_relief_pension is None else without_relief_pension,
                home_carer_credit=home_carer_credit,
                spouse_self_employed=spouse_self_employed_income, spouse_farm_wages=spouse_farm_wages,
            )
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
        income = {
            "farm_profit": taxable_profit, "other_income": other_income, "spouse_paye_income": spouse_paye_income,
            "spouse_self_employed_income": spouse_self_employed_income, "spouse_farm_wages": spouse_farm_wages,
        }
        total_tax = round_money(income_tax["net"] + usc["total"] + prsi["total"] + round_money(clawback))
    home_carer_view = None
    if business_type != "company" and home_carer_credit:
        home_carer_view = {
            "credit_after_taper": round_money(home_carer_credit),
            "applied": person["home_carer"],
        }
    income = {k: round_money(x) for k, x in income.items()}
    income["total"] = round_money(
        max(income["farm_profit"], 0.0) + income["other_income"] + income["spouse_paye_income"]
        + income["spouse_self_employed_income"] + income["spouse_farm_wages"]
    )
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
        "averaging": None,
        "losses": None,
        "pension": None,
        "home_carer": None if income_tax is None else home_carer_view,
        "step_out": None,
    }


def _projection_people(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """The taxpayers of a projection: each partner of a partnership (with their
    share), else the farmer or company alone at 100%."""
    if profile["business_type"] == "partnership":
        return profile["partners"]
    return [{**profile, "label": "", "profit_share_pct": 100.0}]


def projected_tax(
    profile: dict[str, Any],
    state: dict[str, Any],
    *,
    tax_year: int,
    period_end_month: int,
    operating_profit: float,
    livestock_increase: float,
    agricultural_sales: float,
    register: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tax for one ``plan.projection`` year (ADR-0053 phase 5).

    ``state`` carries what one year hands the next, per taxpayer: farming
    profits before capital allowances (oldest first, seeded with the Platform's
    prior years) for averaging, and State aid given for the caps. Years after the
    last tax year with rules use that year's rules, labelled
    ``latest_held_constant``: a planning assumption, not a forecast of Budgets.
    """
    people = _projection_people(profile)
    if not state:
        state.update(
            history=[[x * p["profit_share_pct"] / 100 for x in profile["prior_farming_profits"]] for p in people],
            aid=[p["state_aid_used"] for p in people],
            given=[[] for _ in people],
        )
    basis_year = min(tax_year, LAST_TAX_YEAR)
    rules = year_rules(basis_year)
    company = profile["business_type"] == "company"
    applied: list[dict[str, Any]] = []
    fra = 0.0
    if not profile["vat_registered"]:
        # ponytail: one rate for the year (the one in force in its last month); split by month if a mid-year change matters
        fra_rule = rule_at(FLAT_RATE_ADDITION, date(tax_year, period_end_month, 1))
        if fra_rule is not None:
            fra = flat_rate_addition(agricultural_sales, fra_rule.value)
            applied.append(fra_rule.as_dict())
    allowances = 0.0
    if register:
        ca_result = tax_capital_allowances(tax_year=tax_year, assets=register, period_end_month=period_end_month)
        allowances = ca_result["total"]["allowance"]
        applied += ca_result["rules_applied"]
    profit = operating_profit + livestock_increase + fra

    rows, incomes = [], []
    averaging = "off"
    for i, person in enumerate(people):
        share = person["profit_share_pct"] / 100
        own_profit, own_allowances = profit * share, allowances * share
        regime, table = (
            ("general", GENERAL)
            if company
            else stock_relief_regime(tax_year, profile["registered_partnership"], person["young_trained_farmer_first_year"])
        )
        rule = rule_at(table, date(basis_year, period_end_month, 1))
        applied.append(rule.as_dict())
        relief = stock_relief(livestock_increase * share, rule.value, own_profit - own_allowances)
        history = state["history"][i]
        history.append(own_profit - relief)
        averaged, relief_effect = history[-1], relief
        if profile["income_averaging"]:
            years = int(averaging_rule(basis_year).value)
            if len(history) >= years:
                # This year's relief moves the average by 1/years only.
                averaged, averaging, relief_effect = averaged_profit(history, years), "applied", relief / years
            else:
                averaging = "insufficient_history"
        given = state["given"][i]
        if regime == "registered_partnership":
            # De minimis over a rolling 3 years: the Platform's figure covers the 2 years before the plan.
            aid_used = (state["aid"][i] if len(given) < 2 else 0.0) + sum(given[-2:])
        else:
            aid_used = state["aid"][i]
        estimate = estimate_with_rules(
            rules,
            business_type=profile["business_type"],
            tax_year=tax_year,
            taxable_profit=averaged - own_allowances,
            other_income=person["other_income"],
            marital_status=person["marital_status"],
            spouse_paye_income=person["spouse_paye_income"],
            stock_relief=relief_effect,
            stock_relief_regime=regime,
            state_aid_used=aid_used,
        )
        cap = estimate["stock_relief_cap"]
        given.append(0.0 if cap is None else cap["tax_value"] - cap["clawback"])
        if regime == "young_trained_farmer":
            state["aid"][i] += given[-1]
        applied += estimate["rules_applied"]
        incomes.append(estimate["income"]["total"])
        rows.append(
            {
                "label": person["label"],
                "profit_share_pct": person["profit_share_pct"],
                "stock_relief_regime": regime,
                "stock_relief": round_money(relief),
                "averaged_profit": round_money(averaged),
                "assessable_profit": round_money(averaged - own_allowances),
                "total_tax": estimate["total_tax"],
            }
        )
    total_tax = round_money(sum(r["total_tax"] for r in rows))
    rate = per_unit(total_tax, sum(incomes))
    return {
        "tax_year": tax_year,
        "rules_basis": "in_force" if basis_year == tax_year else "latest_held_constant",
        "rules_status": "announced" if any(r["status"] == "announced" for r in applied) else "enacted",
        "flat_rate_addition": round_money(fra),
        "profit_before_allowances": round_money(profit),
        "livestock_increase": round_money(livestock_increase),
        "stock_relief_regime": rows[0]["stock_relief_regime"] if len(rows) == 1 else "per_partner",
        "stock_relief": round_money(sum(r["stock_relief"] for r in rows)),
        "capital_allowances": round_money(allowances),
        "averaging": averaging,
        "averaged_profit": round_money(sum(r["averaged_profit"] for r in rows)),
        "assessable_profit": round_money(sum(r["assessable_profit"] for r in rows)),
        "total_tax": total_tax,
        "effective_rate_pct": None if rate is None else round_margin_pct(rate * 100),
        "partners": rows if profile["business_type"] == "partnership" else None,
    }


def tax_averaging_exit(
    *,
    final_averaged_year: int,
    final_averaged_profit: float,
    prior_assessed_profits: list[float],
    deferred_step_out_tax: float = 0.0,
) -> dict[str, Any]:
    """``tax.averaging_exit`` (s.657(8); ADR-0055): leaving averaging after the
    final averaged year. Each of the years before it is raised to at least the
    final averaged profit (before capital allowances); the year after is taxed
    on the normal basis; deferred step-out tax falls due at once. The tax on
    each top-up is ``tax.estimate`` for that year (or the accountant's)."""
    rule = averaging_rule(final_averaged_year)
    first = final_averaged_year - len(prior_assessed_profits)
    extra = exit_top_ups(final_averaged_profit, prior_assessed_profits)
    years = [
        {
            "tax_year": first + i,
            "assessed": round_money(a),
            "topped_up_to": round_money(a + e),
            "additional_assessable": round_money(e),
        }
        for i, (a, e) in enumerate(zip(prior_assessed_profits, extra))
    ]
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "final_averaged_year": final_averaged_year,
        "final_averaged_profit": round_money(final_averaged_profit),
        "years": years,
        "total_additional_assessable": round_money(sum(r["additional_assessable"] for r in years)),
        "normal_basis_from": final_averaged_year + 1,
        "deferred_step_out_tax_due_now": round_money(deferred_step_out_tax),
        "rules_applied": [rule.as_dict()],
    }


def tax_payments(
    *,
    tax_year: int,
    current_year_tax: float,
    preceding_year_tax: float,
    preceding_year_preliminary_paid: float,
    preliminary_basis: str,
    pre_preceding_year_tax: float | None = None,
    direct_debit: bool = False,
    direct_debit_start_month: int | None = None,
) -> dict[str, Any]:
    """``tax.payments`` (ADR-0055): what is paid to Revenue for a tax year and
    when. Preliminary tax on each safe-harbour basis (the Platform chooses one),
    last year's balance, and the gross total due on the pay date (31 October,
    or the ROS date Revenue announced). By direct debit the preliminary tax is
    paid in monthly instalments instead, so only the balance is due that day."""
    bases = {
        "current_90": current_year_tax,
        "prior_100": preceding_year_tax,
        "pre_preceding_105_dd": pre_preceding_year_tax,
    }
    options, rules = [], []
    for basis in prelim.BASES:
        rule = prelim.safe_harbour_rule(basis, tax_year)
        rules.append(rule.as_dict())
        base = bases[basis]
        dd_only = basis == prelim.DIRECT_DEBIT_BASIS
        # The 105% basis: direct debit only, and not when that year's tax was nil.
        available = base is not None and (not dd_only or (direct_debit and base > 0))
        options.append(
            {
                "basis": basis,
                "rate_pct": rule.value,
                "base_tax": None if base is None else round_money(base),
                "amount": None if base is None else round_money(base * rule.value / 100),
                "requires_direct_debit": dd_only,
                "available": available,
            }
        )
    safe = [o for o in options if o["available"]]
    lowest = min(safe, key=lambda o: o["amount"])
    chosen = next(o for o in options if o["basis"] == preliminary_basis)
    preliminary = chosen["amount"]

    balance = round_money(preceding_year_tax - preceding_year_preliminary_paid)
    balance_due, overpaid = max(balance, 0.0), max(-balance, 0.0)
    ros = prelim.ROS_PAY_AND_FILE.get(tax_year)
    plan = None
    if direct_debit:
        months = list(range(direct_debit_start_month, 13))
        cents = prelim.instalments(round(preliminary * 100), len(months))
        plan = [
            {"year": tax_year, "month": m, "day": prelim.DIRECT_DEBIT_DAY, "amount": c / 100}
            for m, c in zip(months, cents)
        ]
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "tax_year": tax_year,
        "options": options,
        "lowest_safe": {"basis": lowest["basis"], "amount": lowest["amount"]},
        "preliminary": {"basis": preliminary_basis, "amount": preliminary},
        "preceding_year": {
            "tax_year": tax_year - 1,
            "liability": round_money(preceding_year_tax),
            "preliminary_paid": round_money(preceding_year_preliminary_paid),
            "balance_due": round_money(balance_due),
            "overpaid": round_money(overpaid),
        },
        "pay_date": {
            "statutory": date(tax_year, 10, prelim.STATUTORY_DAY_OF_OCTOBER).isoformat(),
            "ros": None if ros is None else ros[0].isoformat(),
            "ros_source": None if ros is None else ros[1],
        },
        # Gross: an overpayment of last year is shown, never netted here.
        "due_on_pay_date": round_money(balance_due + (0.0 if direct_debit else preliminary)),
        "direct_debit_instalments": plan,
        # This year's tax not covered by the preliminary: due with next year's return.
        "balance_next_year": round_money(current_year_tax - preliminary),
        "rules_applied": rules,
    }


def projected_payments(
    basis: str,
    pay_year: int,
    tax_year: int,
    liabilities: dict[int, float],
    preliminary_paid: dict[int, float],
) -> dict[str, Any]:
    """Tax paid in one ``plan.projection`` year (ADR-0055): on the October pay
    date inside the year, preliminary tax for ``pay_year`` plus the balance of
    the year before. ``liabilities`` and ``preliminary_paid`` are by tax year
    (history, then projected); this year's preliminary is recorded for the next.
    Years after the last rules year use that year's rates."""
    rule = prelim.safe_harbour_rule(basis, min(pay_year, LAST_TAX_YEAR))
    amount = round_money(prelim.preliminary_amount(basis, rule.value, liabilities, pay_year))
    balance = round_money(liabilities[pay_year - 1] - preliminary_paid[pay_year - 1])
    preliminary_paid[pay_year] = amount
    balance_due, refund = max(balance, 0.0), max(-balance, 0.0)
    return {
        "pay_year": pay_year,
        "preliminary_basis": basis,
        "preliminary": amount,
        "balance_previous_year": balance_due,
        "refund_previous_year": refund,
        "paid": round_money(balance_due + amount),
        # Accrued and not yet paid at the year end: this pay year's balance, plus a
        # later tax year whose pay date falls after the year (non-calendar year ends).
        "owed_at_year_end": round_money(sum(liabilities[y] for y in range(pay_year, tax_year + 1)) - amount),
    }


def succession_credit_amount(succession: dict[str, Any] | None, tax_year: int) -> tuple[float, Rule | None]:
    """Total succession partnership credit for the year (0 outside its 5 years or
    once the successor is 40 on 1 January), with the rule fixed at registration."""
    if not succession:
        return 0.0, None
    registered = succession["registered_year"]
    rule = rule_at(SUCCESSION_CREDIT, date(registered, 1, 1))
    age_on_1_january = tax_year - succession["successor_birth_year"] - 1  # exact unless born on 1 January
    if rule is None or not registered <= tax_year < registered + SUCCESSION_CREDIT_YEARS:
        return 0.0, rule
    return (0.0 if age_on_1_january >= SUCCESSOR_AGE_LIMIT else rule.value), rule


def tax_partnership(
    *,
    tax_year: int,
    trading_profit: float,
    partners: list[dict[str, Any]],
    period_end_month: int = 12,
    registered_partnership: bool = True,
    succession: dict[str, Any] | None = None,
    livestock_opening_value: float = 0.0,
    livestock_closing_value: float = 0.0,
    stock_opening_value: float = 0.0,
    stock_closing_value: float = 0.0,
    capital_allowances: float | None = None,
) -> dict[str, Any]:
    """``tax.partnership``: split taxable profit and the stock increase by profit
    share, then stock relief, succession credit and tax for each partner. A
    partner in income averaging is assessed on the average of their own share
    (before their share of the allowances) over the averaging period (ADR-0055)."""
    rules = year_rules(tax_year)
    increase = (livestock_closing_value + stock_closing_value) - (livestock_opening_value + stock_opening_value)
    credit_total, credit_rule = succession_credit_amount(succession, tax_year)
    applied: dict[tuple[str, Any], dict] = {}
    rows = []
    for partner in partners:
        pct = partner["profit_share_pct"]
        profit = trading_profit * pct / 100
        regime, table = stock_relief_regime(tax_year, registered_partnership, partner["young_trained_farmer_first_year"])
        rule = rule_at(table, date(tax_year, period_end_month, 1))
        relief = stock_relief(increase * pct / 100, rule.value, profit)
        taxable = profit - relief
        assessable, relief_effect, averaging, averaging_rule_used = taxable, relief, None, None
        if partner["income_averaging"]:
            own_allowances = capital_allowances * pct / 100
            assessable, averaging, averaging_rule_used = averaging_view(
                tax_year, taxable + own_allowances, partner["prior_farming_profits"], own_allowances
            )
            relief_effect = relief / averaging["years"]
        credit = succession_credit(credit_total, pct, assessable)
        tax = estimate_with_rules(
            rules,
            business_type="partnership",
            tax_year=tax_year,
            taxable_profit=assessable,
            other_income=partner["other_income"],
            marital_status=partner["marital_status"],
            spouse_paye_income=partner["spouse_paye_income"],
            stock_relief=relief_effect,
            stock_relief_regime=regime,
            state_aid_used=partner["state_aid_used"],
            extra_credit=credit,
        )
        if averaging_rule_used is not None:
            tax = {**tax, "averaging": averaging, "rules_applied": [*tax["rules_applied"], averaging_rule_used.as_dict()]}
        for r in [rule.as_dict(), *tax["rules_applied"]]:
            applied[(r["rule_id"], r["from"])] = r
        rows.append(
            {
                "label": partner["label"],
                "profit_share_pct": pct,
                "profit_share": round_money(profit),
                "stock_increase_share": round_money(increase * pct / 100),
                "stock_relief_regime": regime,
                "stock_relief": round_money(relief),
                "taxable_profit": round_money(taxable),
                "succession_credit": round_money(credit),
                "tax": tax,
            }
        )
    if credit_total and credit_rule is not None:
        applied[(credit_rule.rule_id, credit_rule.start.isoformat())] = credit_rule.as_dict()
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "tax_year": tax_year,
        "registered_partnership": registered_partnership,
        "succession_credit_total": round_money(credit_total),
        "trading_profit": round_money(trading_profit),
        "stock_increase": round_money(increase),
        "partners": rows,
        "total": {
            "stock_relief": round_money(sum(r["stock_relief"] for r in rows)),
            "succession_credit": round_money(sum(r["succession_credit"] for r in rows)),
            "total_tax": round_money(sum(r["tax"]["total_tax"] for r in rows)),
        },
        "rules_applied": list(applied.values()),
    }


def tax_company_extraction(
    *,
    tax_year: int,
    trading_profit: float,
    non_trading_income: float = 0.0,
    salary: float = 0.0,
    dividends: float = 0.0,
    marital_status: str = "single",
    spouse_paye_income: float = 0.0,
    other_income: float = 0.0,
) -> dict[str, Any]:
    """``tax.company_extraction``: one way of paying the farmer-director (salary
    and / or dividends) through to company tax, the director's tax and the cash
    the household keeps. Call once per mix to compare."""
    rules = year_rules(tax_year)
    v = {k: r.value for k, r in rules.items()}
    taxable = max(trading_profit - salary, 0.0)
    corporation = estimate_with_rules(
        rules, business_type="company", tax_year=tax_year,
        taxable_profit=trading_profit - salary, other_income=non_trading_income,
    )["corporation_tax"]
    trading_ct, non_trading_ct = corporation["trading"], corporation["non_trading"]
    after_tax = trading_profit - salary + non_trading_income - trading_ct - non_trading_ct
    # s.440: after-tax investment / estate income, less 7.5% for a trading company,
    # not paid out as dividends (this year's dividends assumed paid within 18 months).
    investment = (non_trading_income - non_trading_ct) * (100 - v["ct_close_surcharge_trading_reduction"]) / 100
    excess = max(investment - dividends, 0.0)
    surcharge = excess * v["ct_close_surcharge_rate"] / 100 if excess > v["ct_close_surcharge_de_minimis"] else 0.0
    dwt = dividends * v["dwt_rate"] / 100

    # Proprietary director: salary is earned (earned income credit, PAYE for USC),
    # dividends are taxed as income; PRSI Class S on both.
    person = _individual(
        v, salary, dividends + other_income, marital_status == "married", spouse_paye_income, paye=salary
    )
    income_tax = {k: round_money(x) for k, x in person["income_tax"].items()}
    usc, prsi = _rounded(person["usc"]), _rounded(person["prsi"])
    director_tax = round_money(income_tax["net"] + usc["total"] + prsi["total"])
    company_tax = round_money(trading_ct + non_trading_ct + surcharge)
    profits = trading_profit + non_trading_income
    rate = per_unit(company_tax + director_tax, profits)
    used = [
        "ct_rate_trading", "ct_rate_non_trading", "ct_close_surcharge_rate",
        "ct_close_surcharge_trading_reduction", "ct_close_surcharge_de_minimis", "dwt_rate",
        *(k for k in RULES if k.startswith(("it_", "usc_", "prsi_"))),
    ]
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "tax_year": tax_year,
        "company": {
            "trading_profit": round_money(trading_profit),
            "salary": round_money(salary),
            "taxable_trading_profit": round_money(taxable),
            "non_trading_income": round_money(non_trading_income),
            "corporation_tax": round_money(trading_ct + non_trading_ct),
            "profit_after_tax": round_money(after_tax),
            "dividends": round_money(dividends),
            "dwt_withheld": round_money(dwt),
            "close_company_surcharge": round_money(surcharge),
            "retained": round_money(after_tax - dividends - surcharge),
        },
        "director": {
            "salary": round_money(salary),
            "dividends": round_money(dividends),
            "other_income": round_money(other_income),
            "spouse_paye_income": round_money(spouse_paye_income),
            "assessment": "joint" if marital_status == "married" else "single",
            "income_tax": income_tax,
            "usc": usc,
            "prsi": prsi,
            "total_tax": director_tax,
            "dwt_credit": round_money(dwt),
            "balance_due": round_money(director_tax - dwt),
        },
        "household": {
            # Joint assessment taxes the spouse's pay too, so count it on both sides.
            "income_after_tax": round_money(salary + dividends + other_income + spouse_paye_income - director_tax),
            "total_tax": round_money(company_tax + director_tax),
            "effective_rate_pct": None if rate is None else round_margin_pct(rate * 100),
        },
        "rules_applied": [rules[k].as_dict() for k in used],
    }


__all__ = [
    "estimate_with_rules",
    "tax_averaging_exit",
    "tax_company_extraction",
    "succession_credit_amount",
    "tax_partnership",
    "projected_payments",
    "projected_tax",
    "resolve_allowance",
    "stock_relief_regime",
    "tax_capital_allowances",
    "tax_estimate",
    "tax_payments",
    "tax_stock_relief",
]
