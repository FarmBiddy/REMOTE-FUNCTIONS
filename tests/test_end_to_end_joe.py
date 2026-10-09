"""End-to-end: Joe Bloggs' farm through every public ID; figures must agree.

Each ID is run once on the same farm (tests/joe_farm.py). Cross-checks assert
that the same quantity is identical wherever it appears: surplus, cash, debt,
depreciation, capacity, forecasts and reports. Adding a public ID without
covering it here fails `test_every_public_id_is_covered`.
"""

import pytest

from farm_functions.registry import PUBLIC_CALCULATION_IDS
from farm_functions.runner import run_function
from tests import joe_farm as joe

CENT = 0.01
YEAR_MILK = sum(m["milk_litres"] * m["milk_price"] for m in joe.ACTUAL)
YEAR_LITRES = sum(m["milk_litres"] for m in joe.ACTUAL)
FORECAST_MONTHS = [{"year": 2026, "month": m} for m in (10, 11, 12)]
PARLOUR_SCENARIO = {
    "name": "new parlour",
    "investments": [{
        "year": 2026, "month": 4, "amount": 120_000, "cash_line": "other_capital_payments",
        "loan": {"amount": 100_000, "annual_rate": 0.05, "remaining_months": 120},
        "monthly_effects": {"labour": -1_000},
    }],
}
FARM_FILE = {
    "pl_months": joe.ACTUAL, "cf_months": joe.CASH, "opening_cash": joe.OPENING_CASH,
    "milking_cows": joe.COWS, "hectares": joe.HECTARES, "prior_pl_months": joe.PRIOR,
    "loans": joe.LOANS, "assets": joe.ASSETS, **joe.VALUES, **joe.HOUSEHOLD,
    "new_loan": {"annual_rate": 0.05, "term_months": 120, "min_cover": 1.25},
    "scenarios": [{"name": "milk -5c", "milk_price_c": -5}],
}
ANNUAL = {  # pl.summary inputs equivalent to the reporting year
    "milking_cows": joe.COWS,
    "litres_per_cow": YEAR_LITRES / joe.COWS,
    "milk_price": YEAR_MILK / YEAR_LITRES,
    **{k: sum(m[k] for m in joe.ACTUAL) for k in (
        "biss", "acres", "cattle_sales", "feed", "fertiliser", "vet", "contractor", "labour",
        "insurance", "fuel", "electricity", "water", "repairs_maintenance", "rent_lease",
        "professional_fees", "levies", "other_operating_costs", "loan_repayments")},
}
SCHEMES = {k: ANNUAL[k] for k in ("biss", "acres")}
COSTS = {k: v for k, v in ANNUAL.items() if k not in ("milking_cows", "litres_per_cow", "milk_price", "biss", "acres", "cattle_sales", "loan_repayments")}
PERIOD = {"from_year": 2025, "from_month": 10, "to_year": 2026, "to_month": 9}

PAYLOADS = {
    "revenue.milk": {k: ANNUAL[k] for k in ("milking_cows", "litres_per_cow", "milk_price")},
    "revenue.schemes": SCHEMES,
    "revenue.other": {"cattle_sales": ANNUAL["cattle_sales"]},
    "revenue.total": {k: ANNUAL[k] for k in ("milking_cows", "litres_per_cow", "milk_price", "biss", "acres", "cattle_sales")},
    "costs.total": COSTS,
    "profit.net": "TOTALS",
    "profit.margin": "TOTALS",
    "pl.summary": ANNUAL,
    "pl.monthly": joe.ACTUAL[7],
    "pl.months": {"months": joe.ACTUAL},
    "cf.monthly": joe.CASH[7],
    "cf.months": {"opening_cash": joe.OPENING_CASH, "months": joe.CASH},
    "loan.schedule": {"loans": joe.LOANS},
    "assets.schedule": {"assets": joe.ASSETS, **PERIOD},
    "debt.capacity": {"months": joe.ACTUAL, **joe.HOUSEHOLD, "annual_rate": 0.05, "term_months": 120, "min_cover": 1.25},
    "kpi.summary": {"months": joe.ACTUAL, "milking_cows": joe.COWS, "hectares": joe.HECTARES, "debt_balance": 86_800},
    "pl.net": {"months": joe.ACTUAL, "interest": 12 * 330, **{k: joe.VALUES[k] for k in (
        "livestock_opening_value", "stock_opening_value")},
        "livestock_closing_value": joe.VALUES["livestock"], "stock_closing_value": joe.VALUES["stock"]},
    "milk.quality": {
        "months": joe.STATEMENTS, "milking_cows": joe.COWS, "hectares": joe.HECTARES,
        # Platform-style: ICBF / CSO averages, plus ICBF best 20% for SCC; no top 10%.
        "benchmarks": {"scc_k": {"average": 170, "best20": 110}, "tbc_k": {"average": 15},
                       "fat_pct": {"average": 4.4}, "protein_pct": {"average": 3.55}},
        "pricing": {"fat_eur_per_kg": 4.8, "protein_eur_per_kg": 7.3, "volume_charge_c_per_l": 3.2,
                    "scc_bands": [{"max_k": 100, "adjustment_c": 0.4}, {"max_k": 200, "adjustment_c": 0.2},
                                  {"max_k": 400, "adjustment_c": 0}, {"adjustment_c": -1}],
                    "tbc_bands": [{"max_k": 10, "adjustment_c": 0.2}, {"adjustment_c": 0}]},
    },
    "bs.summary": {"year": 2026, "month": 9, "loans": joe.LOANS, "assets": joe.ASSETS,
                   **{k: joe.VALUES[k] for k in ("debtors", "stock", "livestock", "land", "creditors")}},
    "pl.compare": {"actual": joe.ACTUAL, "comparison": joe.PRIOR},
    "cf.compare": {"actual": joe.CASH, "comparison": joe.CASH},
    "risk.sensitivity": {"pl_months": joe.ACTUAL, "cf_months": joe.CASH, "opening_cash": joe.OPENING_CASH,
                         "loans": joe.LOANS, "scenarios": [{"name": "milk -5c", "milk_price_c": -5},
                                                           {"name": "rates +2", "rate_shift_pp": 2},
                                                           PARLOUR_SCENARIO]},
    "risk.tornado": {"pl_months": joe.ACTUAL, "cf_months": joe.CASH, "opening_cash": joe.OPENING_CASH, "loans": joe.LOANS},
    "decision.partial_budget": {"added_income": [{"label": "labour saved", "amount": 12_000}],
                                "capital": {"amount": 120_000, "life_years": 20, "annual_rate": 0.05}},
    "decision.investment": {"amount": 120_000, "discount_rate": 0.05, "annual_benefit": 12_000, "life_years": 20},
    "report.bank": FARM_FILE,
    "report.advisor": FARM_FILE,
    "report.accountant": FARM_FILE,
    "plan.projection": {"base_pl_months": joe.ACTUAL, "opening_cash": 0, "milking_cows": joe.COWS, "years": 5,
                        "loans": joe.LOANS, "assets": joe.ASSETS, "land": joe.VALUES["land"],
                        "livestock": joe.VALUES["livestock"]},
    "pl.forecast": {"history": joe.PRIOR + joe.ACTUAL, "forecast": FORECAST_MONTHS},
    "cf.forecast": {"history": joe.CASH, "forecast": [{"year": 2026, "month": 10}]},
}


@pytest.fixture(scope="module")
def results():
    out = {}
    # Atomic profit IDs last: they take the published annual totals of pl.summary.
    for key, payload in sorted(PAYLOADS.items(), key=lambda kv: kv[1] == "TOTALS"):
        if payload == "TOTALS":
            summary = out["pl.summary"]
            payload = {"revenue": summary["revenue"]["total"], "costs": summary["costs"]["total"]}
        result = run_function(key, payload)
        assert result["status"] == "ok", (key, result)
        out[key] = result["result"]
    return out


def test_every_public_id_is_covered():
    assert set(PAYLOADS) == set(PUBLIC_CALCULATION_IDS)


def _year_pl(results):
    months = results["pl.months"]["months"]
    return {
        "milk": sum(m["revenue"]["milk"] for m in months),
        "revenue": sum(m["revenue"]["total"] for m in months),
        "costs": sum(m["costs"]["total"] for m in months),
        "operating_surplus": sum(m["profit"]["net"] for m in months),
    }


def test_annual_and_monthly_agree(results):
    year = _year_pl(results)
    summary = results["pl.summary"]
    assert summary["revenue"]["milk"] == pytest.approx(year["milk"], abs=CENT)
    assert summary["revenue"]["total"] == pytest.approx(year["revenue"], abs=CENT)
    assert summary["profit"]["net"] == pytest.approx(year["operating_surplus"], abs=CENT)
    assert results["revenue.total"]["amount"] == summary["revenue"]["total"]
    assert results["costs.total"]["amount"] == summary["costs"]["total"]
    assert results["revenue.schemes"]["amount"] == summary["revenue"]["schemes"]
    assert results["profit.net"]["amount"] == summary["profit"]["net"]
    assert results["profit.margin"]["margin_pct"] == summary["profit"]["margin_pct"]
    assert results["pl.monthly"] == results["pl.months"]["months"][7]
    assert results["cf.monthly"]["net_cash_flow"] == results["cf.months"]["months"][7]["net_cash_flow"]


def test_surplus_is_the_same_everywhere(results):
    surplus = results["pl.summary"]["profit"]["net"]
    assert results["kpi.summary"]["totals"]["operating_surplus"] == pytest.approx(surplus, abs=CENT)
    assert results["pl.net"]["operating_surplus"] == pytest.approx(surplus, abs=CENT)
    assert results["debt.capacity"]["operating_surplus"] == pytest.approx(surplus, abs=CENT)
    assert results["pl.compare"]["profit"]["net"]["actual"] == pytest.approx(surplus, abs=CENT)
    assert results["risk.sensitivity"]["scenarios"][0]["operating_surplus"] == pytest.approx(surplus, abs=CENT)
    assert results["risk.tornado"]["base"]["operating_surplus"] == results["risk.sensitivity"]["scenarios"][0]["operating_surplus"]
    assert results["plan.projection"]["years"][0]["pl"]["operating_surplus"] == pytest.approx(surplus, abs=CENT)
    for kind in ("bank", "accountant"):
        profit = results[f"report.{kind}"]["profit" if kind == "bank" else "net_profit"]
        assert profit["operating_surplus"] == pytest.approx(surplus, abs=CENT)


def test_cash_is_the_same_everywhere(results):
    closing = results["cf.months"]["closing_cash"]
    bank = results["report.bank"]
    assert bank["cash"]["actual"]["closing_cash"] == closing
    assert bank["balance_sheet"]["assets"]["current"]["cash"] == max(closing, 0)
    assert results["report.accountant"]["cash_flow"]["closing_cash"] == closing
    assert results["risk.sensitivity"]["scenarios"][0]["closing_cash"] == closing
    assert closing == pytest.approx(joe.OPENING_CASH + sum(m["net_cash_flow"] for m in results["cf.months"]["months"]), abs=CENT)


def test_debt_and_assets_are_the_same_everywhere(results):
    loans = results["loan.schedule"]
    sheet = results["bs.summary"]
    loan_liabilities = (sheet["liabilities"]["current"]["loans_due_within_12_months"]
                        + sheet["liabilities"]["non_current"]["loans_due_after_12_months"])
    assert loan_liabilities == pytest.approx(loans["total_balance"], abs=CENT) == 86_800
    assert results["report.bank"]["kpis"]["debt"]["balance"] == loans["total_balance"]
    assets = results["assets.schedule"]["total"]
    fixed = sheet["assets"]["non_current"]
    assert fixed["buildings"] + fixed["machinery"] == pytest.approx(assets["closing_nbv"], abs=CENT)
    assert results["report.accountant"]["net_profit"]["depreciation"] == assets["depreciation"]
    assert results["report.accountant"]["fixed_assets"]["total"] == assets


def test_reports_reuse_the_direct_ids(results):
    bank = results["report.bank"]
    assert bank["capacity"] == results["debt.capacity"]
    assert bank["loans"] == results["loan.schedule"]
    assert results["report.advisor"]["comparison"] == results["pl.compare"]
    assert results["report.accountant"]["balance_sheet"] == bank["balance_sheet"]
    # bs.summary called directly with the report's closing cash gives the same sheet.
    direct = run_function("bs.summary", {**PAYLOADS["bs.summary"], "cash": results["cf.months"]["closing_cash"]})
    assert direct["result"] == bank["balance_sheet"]


def test_forecasts_plug_into_the_period_ids(results):
    projected = results["pl.forecast"]["months"][0]
    replay = run_function("pl.monthly", {"year": 2026, "month": 10, **projected["inputs"]})["result"]
    assert replay == projected["statement"]
    cash = results["cf.forecast"]["months"][0]
    rolled = run_function("cf.months", {"opening_cash": joe.OPENING_CASH, "months": [*joe.CASH, {"year": 2026, "month": 10, **cash["inputs"]}]})["result"]
    assert rolled["months"][-1]["net_cash_flow"] == cash["cash_flow"]["net_cash_flow"]


def test_decisions_agree_with_each_other(results):
    parlour = next(s for s in results["risk.sensitivity"]["scenarios"] if s["name"] == "new parlour")
    payback_months = parlour["investments"][0]["simple_payback_months"]
    assert payback_months == pytest.approx(results["decision.investment"]["simple_payback_years"] * 12, abs=0.1)
    assert results["decision.partial_budget"]["capital"]["simple_payback_years"] == results["decision.investment"]["simple_payback_years"]


def test_seasonal_farm_story(results):
    """Sanity of the scenario itself: milk -5c hurts; rates only reprice future instalments."""
    base, milk, rates, parlour = results["risk.sensitivity"]["scenarios"]
    assert milk["operating_surplus"] == pytest.approx(base["operating_surplus"] - 0.05 * YEAR_LITRES, abs=CENT)
    # Loans are as at 30 Sep 2026 (next instalment October): past months do not move.
    assert rates == {**base, "name": "rates +2", "shocks": rates["shocks"]}
    shifted = run_function(
        "plan.projection",
        {**PAYLOADS["plan.projection"], "assumptions": {"interest_rate_shift_pp": [2]}},
    )["result"]["years"][0]["debt"]["debt_service"]
    assert shifted > results["plan.projection"]["years"][0]["debt"]["debt_service"]
    assert parlour["closing_cash"] < base["closing_cash"]  # €20,000 deposit out of pocket
    drivers = [d["driver"] for d in results["risk.tornado"]["drivers"]]
    assert drivers[0] in ("milk_price", "milk_volume")


def test_milk_quality_feeds_the_kpis(results):
    """Solids from the milk statements give the kg MS KPIs; same litres as the P&L."""
    quality = results["milk.quality"]
    assert quality["period"]["milk_litres"] == YEAR_LITRES
    kpis = run_function("kpi.summary", {**PAYLOADS["kpi.summary"], "milk_solids_kg": quality["period"]["milk_solids_kg"]})["result"]
    assert kpis["per_kg_ms"]["revenue"] == pytest.approx(kpis["totals"]["revenue"] / quality["period"]["milk_solids_kg"], abs=0.01)
    assert quality["compliance"]["scc_breach_months"] == []  # late-lactation peak stays under the EU limit
    assert quality["value"]["gain_to_average_eur"] > 0  # fat below average
    assert quality["vs_benchmarks"]["protein_pct"]["position"] == "about"
