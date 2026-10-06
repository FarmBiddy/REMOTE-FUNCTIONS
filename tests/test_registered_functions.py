"""Behavior matrix: every registered function gets happy-path and edge-case coverage."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import (
    FUNCTIONS,
    INPUT_MODELS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
)
from farm_functions.runner import run_function
from farm_functions.schemas import missing_field_entry

client = TestClient(app)

FUNCTION_KEYS = sorted(FUNCTIONS.keys())

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}

SAMPLE_SCHEMES = {"biss": 20_000, "acres": 5_000, "other_grants": 0}
SAMPLE_OTHER = {"cattle_sales": 15_000, "land_leasing_income": 0, "other": 0}
SAMPLE_COSTS = {
    "feed": 80_000,
    "fertiliser": 15_000,
    "vet": 5_000,
    "contractor": 10_000,
    "labour": 40_000,
    "insurance": 4_000,
    "fuel": 6_000,
    "electricity": 3_000,
}
SAMPLE_PROFIT_TOTALS = {"revenue": 240_000, "costs": 163_000}
SAMPLE_CASH_MONTH = {
    "year": 2026,
    "month": 3,
    "milk": 18_000,
    "feed": 5_000,
    "machinery_equipment_payments": 6_000,
    "loan_proceeds": 10_000,
    "interest_paid": 500,
}
# Zero rate keeps the schedule hand-checkable: 1200 / 12 = 100 per month.
SAMPLE_LOAN = {
    "balance": 1_200,
    "annual_rate": 0,
    "remaining_months": 12,
    "year": 2026,
    "month": 10,
    "original_principal": 2_400,
}
# KPIs: 10,000 L, €4,000 revenue, €2,000 costs (feed), €500 repayments, 10 cows
# → costs 20 c/L, surplus €200/cow, DSCR 2,000 / 500 = 4.
SAMPLE_KPI = {
    "months": [
        {"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 2_000, "loan_repayments": 500}
    ],
    "milking_cows": 10,
}
# Sensitivity: 10,000 L at €0.40 − €3,000 feed = €1,000 surplus → break-even 30 c/L.
SAMPLE_SENSITIVITY = {
    "pl_months": [{"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 3_000}],
    "cf_months": [{"year": 2026, "month": 3, "milk": 4_000, "feed": 3_000}],
    "opening_cash": 0,
    "scenarios": [{"name": "milk -5c", "milk_price_c": -5}],
}
# Compare: same month, milk 10,000 L at €0.40 vs 8,000 L at €0.50 (both €4,000):
# volume effect +1,000, price effect −1,000.
SAMPLE_PL_COMPARE = {
    "actual": [{"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 1_000}],
    "comparison": [{"year": 2025, "month": 3, "milk_litres": 8_000, "milk_price": 0.50, "feed": 800}],
}
SAMPLE_CF_COMPARE = {
    "actual": [{"year": 2026, "month": 3, "milk": 4_000, "feed": 1_000}],
    "comparison": [{"year": 2025, "month": 3, "milk": 4_000, "feed": 800}],
}
# Debt capacity: surplus 3,000 − drawings 1,000 = 2,000 capacity; repayments 1,500
# → cover 1.33; 500 headroom at 0% over 10 months → max loan 5,000.
SAMPLE_DEBT_CAPACITY = {
    "months": [
        {"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 1_000, "loan_repayments": 1_500}
    ],
    "annual_rate": 0,
    "term_months": 10,
    "drawings": 1_000,
}
# Assets: 12,000 machine bought Jan 2026, 10 years straight line -> 1,200 in 2026.
SAMPLE_ASSETS = {
    "assets": [{"cost": 12_000, "year": 2026, "month": 1, "life_months": 120}],
    "from_year": 2026,
    "from_month": 1,
    "to_year": 2026,
    "to_month": 12,
}
# Net profit: surplus 3,000 + livestock +500 - depreciation 1,000 - interest 200 = 2,300.
SAMPLE_PL_NET = {
    "months": [{"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 1_000}],
    "depreciation": 1_000,
    "interest": 200,
    "livestock_opening_value": 100_000,
    "livestock_closing_value": 100_500,
}
# Balance sheet: land 100,000 + cash 10,000 vs creditors 5,000 + loan 20,000
# (0%, 20 months from Jan 2027 → 12,000 due within 12 months) → net worth 85,000.
SAMPLE_BS = {
    "year": 2026,
    "month": 12,
    "cash": 10_000,
    "land": 100_000,
    "creditors": 5_000,
    "loans": [{"balance": 20_000, "annual_rate": 0, "remaining_months": 20, "year": 2027, "month": 1}],
}
# Reports: one month, surplus 3,000; cash 4,000 − 1,000 from opening 0 → 3,000.
SAMPLE_REPORT = {
    "pl_months": [{"year": 2026, "month": 3, "milk_litres": 10_000, "milk_price": 0.40, "feed": 1_000}],
    "cf_months": [{"year": 2026, "month": 3, "milk": 4_000, "feed": 1_000}],
    "opening_cash": 0,
    "milking_cows": 10,
}
REPORT_KEYS = ("report.bank", "report.advisor", "report.accountant")
# Projection: 12 months of 10,000 L at 0.40 − 1,000 feed → surplus 36,000 a year.
SAMPLE_PROJECTION = {
    "base_pl_months": [
        {"year": 2025, "month": m, "milk_litres": 10_000, "milk_price": 0.40, "feed": 1_000}
        for m in range(1, 13)
    ],
    "opening_cash": 0,
    "milking_cows": 10,
    "years": 2,
}
# Forecast: no overlapping year-on-year months → run-rate 1, so Oct-2026 = Oct-2025
# lines, milk at the latest actual price (Sep-2026 €0.45): 40,000 × 0.45 − 5,000.
SAMPLE_PL_FORECAST = {
    "history": [
        {"year": 2025, "month": 10, "milk_litres": 40_000, "milk_price": 0.40, "feed": 5_000},
        {"year": 2026, "month": 9, "milk_litres": 30_000, "milk_price": 0.45},
    ],
    "forecast": [{"year": 2026, "month": 10}],
}
# Cash: last October's machinery purchase is a one-off and is not projected.
SAMPLE_CF_FORECAST = {
    "history": [
        {"year": 2025, "month": 10, "milk": 18_000, "feed": 5_000, "machinery_equipment_payments": 6_000}
    ],
    "forecast": [{"year": 2026, "month": 10, "interest_paid": 500}],
}


def _happy_payload(key: str) -> dict:
    """Sample-farm-style inputs for a registered function."""
    if key == "revenue.milk":
        return dict(SAMPLE_MILK)
    if key == "revenue.schemes":
        return dict(SAMPLE_SCHEMES)
    if key == "revenue.other":
        return dict(SAMPLE_OTHER)
    if key == "revenue.total":
        return {**SAMPLE_MILK, **SAMPLE_SCHEMES, **SAMPLE_OTHER}
    if key == "costs.total":
        return dict(SAMPLE_COSTS)
    if key in ("profit.net", "profit.margin"):
        return dict(SAMPLE_PROFIT_TOTALS)
    if key == "pl.summary":
        return load_sample_inputs()
    if key == "pl.monthly":
        return {
            "year": 2026,
            "month": 3,
            "milk_litres": 40_000,
            "milk_price": 0.40,
            "biss": 2_000,
            "acres": 500,
            "cattle_sales": 1_000,
            "feed": 5_000,
            "fertiliser": 1_000,
            "loan_repayments": 1_500,
        }
    if key == "pl.months":
        return {
            "months": [
                {
                    "year": 2026,
                    "month": 3,
                    "milk_litres": 40_000,
                    "milk_price": 0.40,
                    "biss": 2_000,
                    "acres": 500,
                    "cattle_sales": 1_000,
                    "feed": 5_000,
                    "fertiliser": 1_000,
                    "loan_repayments": 1_500,
                }
            ]
        }
    if key == "cf.monthly":
        return dict(SAMPLE_CASH_MONTH)
    if key == "cf.months":
        return {"opening_cash": 20_000, "months": [dict(SAMPLE_CASH_MONTH)]}
    if key == "loan.schedule":
        return {"loans": [dict(SAMPLE_LOAN)]}
    if key == "pl.forecast":
        return SAMPLE_PL_FORECAST
    if key == "kpi.summary":
        return SAMPLE_KPI
    if key == "risk.sensitivity":
        return SAMPLE_SENSITIVITY
    if key == "pl.compare":
        return SAMPLE_PL_COMPARE
    if key == "debt.capacity":
        return SAMPLE_DEBT_CAPACITY
    if key == "assets.schedule":
        return SAMPLE_ASSETS
    if key == "pl.net":
        return SAMPLE_PL_NET
    if key == "bs.summary":
        return SAMPLE_BS
    if key in REPORT_KEYS:
        return SAMPLE_REPORT
    if key == "plan.projection":
        return SAMPLE_PROJECTION
    if key == "risk.tornado":
        return {k: SAMPLE_SENSITIVITY[k] for k in ("pl_months", "cf_months", "opening_cash")}
    if key == "decision.partial_budget":
        # 5,000 gained − 3,000 lost − capital (10,000 / 10 + 10,000 / 2 × 4%) = 800.
        return {
            "added_income": [{"label": "extra sales", "amount": 5_000}],
            "added_costs": [{"label": "extra costs", "amount": 3_000}],
            "capital": {"amount": 10_000, "life_years": 10, "annual_rate": 0.04},
        }
    if key == "cf.compare":
        return SAMPLE_CF_COMPARE
    if key == "cf.forecast":
        return SAMPLE_CF_FORECAST
    raise AssertionError(f"No happy payload for {key}")


def _required_only_payload(key: str) -> dict:
    """Required fields only (optionals omitted → default 0)."""
    required = REQUIRED_FIELDS[key]
    if not required:
        return {}
    full = _happy_payload(key)
    if key == "pl.months":
        # Nested month items: keep only required pl.monthly fields per item.
        months = []
        for item in full["months"]:
            months.append(
                {
                    "year": item["year"],
                    "month": item["month"],
                    "milk_litres": item["milk_litres"],
                    "milk_price": item["milk_price"],
                }
            )
        return {"months": months}
    if key == "cf.months":
        return {"opening_cash": 20_000, "months": [{"year": 2026, "month": 3}]}
    return {name: full[name] for name in required}


def _zero_payload(key: str) -> dict:
    """All known fields set explicitly to 0."""
    if key == "pl.months":
        return {
            "months": [
                {
                    "year": 1,
                    "month": 1,
                    "milk_litres": 0,
                    "milk_price": 0,
                }
            ]
        }
    if key == "cf.months":
        return {"opening_cash": 0, "months": [{"year": 1, "month": 1}]}
    if key == "loan.schedule":
        # Instalment count and calendar cannot be zero.
        return {
            "loans": [{**dict.fromkeys(SAMPLE_LOAN, 0), "remaining_months": 1, "year": 1, "month": 1}]
        }
    if key == "kpi.summary":
        return {"months": [{"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}], "milking_cows": 0}
    if key == "decision.partial_budget":
        zero = [{"label": "x", "amount": 0}]
        return {
            "added_income": zero, "reduced_costs": zero, "added_costs": zero, "reduced_income": zero,
            "capital": {"amount": 0, "life_years": 1, "annual_rate": 0},
        }
    if key == "risk.tornado":
        return {
            "pl_months": [{"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}],
            "cf_months": [{"year": 1, "month": 1}],
            "opening_cash": 0,
            "loans": [],
            "rate_step_pp": 0,
        }
    if key == "plan.projection":
        return {
            "base_pl_months": [
                {"year": 1, "month": m, "milk_litres": 0, "milk_price": 0} for m in range(1, 13)
            ],
            "opening_cash": 0,
            "milking_cows": 0,
            "years": 1,
            "land": 0,
            "livestock": 0,
        }
    if key in REPORT_KEYS:
        return {
            "pl_months": [{"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}],
            "cf_months": [{"year": 1, "month": 1}],
            "opening_cash": 0,
            "milking_cows": 0,
        }
    if key == "bs.summary":
        return {
            "year": 1, "month": 1, "cash": 0, "debtors": 0, "stock": 0, "livestock": 0, "land": 0,
            "creditors": 0, "other_long_term_liabilities": 0, "loans": [], "assets": [],
        }
    if key == "pl.net":
        return {
            "months": [{"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}],
            "depreciation": 0, "interest": 0,
            "livestock_opening_value": 0, "livestock_closing_value": 0,
            "stock_opening_value": 0, "stock_closing_value": 0,
        }
    if key == "assets.schedule":
        return {
            "assets": [{"cost": 0, "year": 1, "month": 1, "life_months": 1, "residual_value": 0}],
            "from_year": 1, "from_month": 1, "to_year": 1, "to_month": 1,
        }
    if key == "debt.capacity":
        month = {"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}
        return {
            "months": [month], "annual_rate": 0, "term_months": 1,
            "drawings": 0, "tax": 0, "off_farm_income": 0, "min_cover": 1,
        }
    if key == "pl.compare":
        month = {"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}
        return {"actual": [month], "comparison": [month]}
    if key == "cf.compare":
        return {"actual": [{"year": 1, "month": 1}], "comparison": [{"year": 1, "month": 1}]}
    if key == "risk.sensitivity":
        return {
            "pl_months": [{"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}],
            "cf_months": [{"year": 1, "month": 1}],
            "opening_cash": 0,
            "scenarios": [],
        }
    if key == "pl.forecast":
        month = {"year": 1, "month": 1, "milk_litres": 0, "milk_price": 0}
        return {"history": [month], "forecast": [{"year": 2, "month": 1, "milk_price": 0}]}
    if key == "cf.forecast":
        return {"history": [{"year": 1, "month": 1}], "forecast": [{"year": 2, "month": 1, "feed": 0}]}
    known = REQUIRED_FIELDS[key] + OPTIONAL_FIELDS[key]
    payload = {name: 0 for name in known}
    # Calendar identity cannot be zero; keep a valid period with zero money drivers.
    if key in ("pl.monthly", "cf.monthly"):
        payload["year"] = 1
        payload["month"] = 1
    return payload


def _assert_ok_money(result: dict, amount: float) -> None:
    assert result["status"] == "ok"
    assert result["result"]["amount"] == amount
    assert result["result"]["currency"] == "EUR"


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_happy_path(key: str) -> None:
    payload = _happy_payload(key)
    result = run_function(key, payload)
    assert result["status"] == "ok"
    assert result["function"] == key

    if key == "revenue.milk":
        _assert_ok_money(result, 200_000)
    elif key == "revenue.schemes":
        _assert_ok_money(result, 25_000)
    elif key == "revenue.other":
        _assert_ok_money(result, 15_000)
    elif key == "revenue.total":
        _assert_ok_money(result, 240_000)
    elif key == "costs.total":
        _assert_ok_money(result, 163_000)
    elif key == "profit.net":
        _assert_ok_money(result, 77_000)
    elif key == "profit.margin":
        body = result["result"]
        assert body["margin"] == 0.3208
        assert body["margin_pct"] == 32.08
        assert body["profit"] == 77_000
        assert body["revenue"] == 240_000
        assert body["costs"] == 163_000
        assert body["currency"] == "EUR"
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 25_000
        assert body["revenue"]["other"] == 15_000
        assert body["revenue"]["total"] == 240_000
        assert body["costs"]["total"] == 163_000
        assert body["profit"]["net"] == 77_000
        assert body["profit"]["margin_pct"] == 32.08
        assert body["finance"]["loan_repayments"] == 12_000
        assert "loan_repayments" not in body["costs"]["lines"]
    elif key == "pl.monthly":
        body = result["result"]
        assert body["period"] == {"kind": "month", "year": 2026, "month": 3}
        assert body["revenue"]["milk"] == 16_000
        assert body["revenue"]["schemes"] == 2_500
        assert body["revenue"]["other"] == 1_000
        assert body["revenue"]["total"] == 19_500
        assert body["costs"]["total"] == 6_000
        assert body["profit"]["net"] == 13_500
        assert body["profit"]["margin_pct"] == 69.23
        assert body["finance"]["loan_repayments"] == 1_500
    elif key == "pl.months":
        body = result["result"]
        assert body["currency"] == "EUR"
        assert body["ytd"] is None
        assert len(body["months"]) == 1
        assert body["months"][0]["period"] == {
            "kind": "month",
            "year": 2026,
            "month": 3,
        }
        assert body["months"][0]["profit"]["net"] == 13_500
    elif key == "cf.monthly":
        body = result["result"]
        assert body["period"] == {"kind": "month", "year": 2026, "month": 3}
        assert body["operating"]["inflows"]["lines"]["milk"] == 18_000
        assert body["operating"]["net"] == 13_000
        assert body["investing"]["net"] == -6_000
        assert body["financing"]["net"] == 9_500
        assert body["cash_in"] == 28_000
        assert body["cash_out"] == 11_500
        assert body["net_cash_flow"] == 16_500
        assert body["opening_cash"] is None
        assert body["closing_cash"] is None
    elif key == "cf.months":
        body = result["result"]
        assert body["opening_cash"] == 20_000
        assert body["months"][0]["net_cash_flow"] == 16_500
        assert body["closing_cash"] == 36_500
    elif key == "loan.schedule":
        assert result["result"]["total_monthly_payment"] == 100
        body = result["result"]["loans"][0]
        assert body["monthly_payment"] == 100
        assert body["total_payments"] == 1_200
        assert body["total_interest"] == 0
        assert body["repaid_pct"] == 50
        assert body["months"][-1]["period"] == {"kind": "month", "year": 2027, "month": 9}
    elif key == "decision.partial_budget":
        body = result["result"]
        assert (body["operating_change"], body["capital"]["annual_charge"], body["net_change"]) == (2_000, 1_200, 800)
        assert body["worthwhile"] is True
    elif key == "risk.tornado":
        drivers = {d["driver"]: d["swing"]["surplus"] for d in result["result"]["drivers"]}
        assert drivers["milk_price"] == 800  # ±10% of 4,000 milk revenue
        assert drivers["feed"] == 600
    elif key == "plan.projection":
        years = result["result"]["years"]
        assert [y["pl"]["operating_surplus"] for y in years] == [36_000, 36_000]
        assert years[1]["cash"]["closing"] == 72_000
    elif key in REPORT_KEYS:
        body = result["result"]
        assert body["report"] == key.split(".")[1]
        assert body["as_of"] == {"kind": "month", "year": 2026, "month": 3}
        profit = body["net_profit"] if key == "report.accountant" else body["profit"]
        assert profit["operating_surplus"] == 3_000
    elif key == "bs.summary":
        body = result["result"]
        assert body["liabilities"]["current"]["loans_due_within_12_months"] == 12_000
        assert body["net_worth"] == 85_000
        assert body["ratios"]["current_ratio"] == 0.59
    elif key == "pl.net":
        body = result["result"]
        assert (body["adjusted_surplus"], body["ebit"], body["net_profit_before_tax"]) == (3_500, 2_500, 2_300)
    elif key == "assets.schedule":
        assert result["result"]["total"] == {
            "opening_nbv": 0, "additions": 12_000, "depreciation": 1_200, "closing_nbv": 10_800
        }
    elif key == "debt.capacity":
        body = result["result"]
        assert (body["repayment_capacity"], body["repayment_cover"]) == (2_000, 1.33)
        assert body["new_loan"]["max_principal"] == 5_000
    elif key == "pl.compare":
        body = result["result"]
        assert body["revenue"]["milk"]["change"] == 0
        assert (body["milk"]["volume_effect"], body["milk"]["price_effect"]) == (1_000, -1_000)
        assert body["costs"]["lines"]["feed"]["change_pct"] == 25
    elif key == "cf.compare":
        assert result["result"]["net_cash_flow"]["change"] == -200
    elif key == "risk.sensitivity":
        body = result["result"]
        assert body["scenarios"][0]["break_even"]["surplus_milk_price_c"] == 30
        assert [s["surplus"] for s in body["scenarios"]] == [1_000, 500]
    elif key == "kpi.summary":
        body = result["result"]
        assert body["per_litre_c"]["costs"] == 20
        assert body["per_cow"]["surplus"] == 200
        assert body["dscr"] == 4
    elif key == "pl.forecast":
        month = result["result"]["months"][0]
        assert month["period"] == {"kind": "month", "year": 2026, "month": 10}
        assert month["inputs"]["milk_price"] == 0.45
        assert month["statement"]["profit"]["net"] == 13_000
    elif key == "cf.forecast":
        month = result["result"]["months"][0]
        assert month["inputs"]["machinery_equipment_payments"] == 0
        assert month["cash_flow"]["cash_out"] == 5_500
        assert month["cash_flow"]["net_cash_flow"] == 12_500


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_required_only_optionals_default_to_zero(key: str) -> None:
    payload = _required_only_payload(key)
    result = run_function(key, payload)
    assert result["status"] == "ok", result

    if key == "revenue.milk":
        _assert_ok_money(result, 200_000)
    elif key == "revenue.schemes":
        _assert_ok_money(result, 0)
    elif key == "revenue.other":
        _assert_ok_money(result, 0)
    elif key == "revenue.total":
        _assert_ok_money(result, 200_000)  # milk only; schemes/other omitted
    elif key == "costs.total":
        _assert_ok_money(result, 0)
    elif key == "profit.net":
        _assert_ok_money(result, 77_000)
    elif key == "profit.margin":
        assert result["result"]["profit"] == 77_000
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 0
        assert body["revenue"]["other"] == 0
        assert body["costs"]["total"] == 0
        assert body["profit"]["net"] == 200_000
        assert body["finance"]["loan_repayments"] == 0
    elif key == "pl.monthly":
        body = result["result"]
        assert body["period"] == {"kind": "month", "year": 2026, "month": 3}
        assert body["revenue"]["milk"] == 16_000
        assert body["revenue"]["schemes"] == 0
        assert body["revenue"]["other"] == 0
        assert body["costs"]["total"] == 0
        assert body["profit"]["net"] == 16_000
        assert body["finance"]["loan_repayments"] == 0
    elif key == "pl.months":
        body = result["result"]
        assert body["ytd"] is None
        assert len(body["months"]) == 1
        assert body["months"][0]["revenue"]["total"] == 16_000
        assert body["months"][0]["costs"]["total"] == 0
        assert body["months"][0]["profit"]["net"] == 16_000
    elif key == "cf.monthly":
        body = result["result"]
        assert body["period"] == {"kind": "month", "year": 2026, "month": 3}
        assert body["cash_in"] == 0
        assert body["cash_out"] == 0
        assert body["net_cash_flow"] == 0
    elif key == "cf.months":
        body = result["result"]
        assert body["net_cash_flow"] == 0
        assert body["closing_cash"] == 20_000
    elif key == "loan.schedule":
        assert result["result"]["loans"][0]["repaid_pct"] == 50


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_explicit_zeros_are_ok(key: str) -> None:
    result = run_function(key, _zero_payload(key))
    assert result["status"] == "ok", result

    if key in (
        "revenue.milk",
        "revenue.schemes",
        "revenue.other",
        "revenue.total",
        "costs.total",
        "profit.net",
    ):
        _assert_ok_money(result, 0)
    elif key == "profit.margin":
        assert result["result"]["margin"] == 0
        assert result["result"]["margin_pct"] == 0
        assert result["result"]["profit"] == 0
    elif key == "pl.summary":
        assert result["result"]["revenue"]["total"] == 0
        assert result["result"]["costs"]["total"] == 0
        assert result["result"]["profit"]["net"] == 0
    elif key == "pl.monthly":
        assert result["result"]["period"] == {"kind": "month", "year": 1, "month": 1}
        assert result["result"]["revenue"]["total"] == 0
        assert result["result"]["costs"]["total"] == 0
        assert result["result"]["profit"]["net"] == 0
    elif key == "pl.months":
        body = result["result"]
        assert body["ytd"] is None
        assert body["months"][0]["period"] == {"kind": "month", "year": 1, "month": 1}
        assert body["months"][0]["revenue"]["total"] == 0
        assert body["months"][0]["profit"]["net"] == 0
    elif key == "cf.monthly":
        assert result["result"]["period"] == {"kind": "month", "year": 1, "month": 1}
        assert result["result"]["net_cash_flow"] == 0
    elif key == "cf.months":
        assert result["result"]["closing_cash"] == 0
    elif key == "loan.schedule":
        assert result["result"]["total_monthly_payment"] == 0
        assert result["result"]["loans"][0]["repaid_pct"] is None
    elif key == "decision.partial_budget":
        assert result["result"]["net_change"] == 0 and result["result"]["worthwhile"] is False
    elif key == "risk.tornado":
        assert result["result"]["base"]["surplus"] == 0
    elif key == "plan.projection":
        year = result["result"]["years"][0]
        assert year["cash"]["closing"] == 0 and year["kpis"]["surplus_per_cow"] is None
    elif key in REPORT_KEYS:
        assert result["result"]["period"]["month_count"] == 1
    elif key == "bs.summary":
        body = result["result"]
        assert body["net_worth"] == 0
        assert body["ratios"]["equity_pct"] is None and body["ratios"]["current_ratio"] is None
    elif key == "pl.net":
        assert result["result"]["net_profit_before_tax"] == 0
        assert result["result"]["net_margin_pct"] is None
    elif key == "assets.schedule":
        assert result["result"]["total"]["closing_nbv"] == 0
    elif key == "debt.capacity":
        assert result["result"]["repayment_cover"] is None
        assert result["result"]["new_loan"]["max_principal"] == 0
    elif key in ("pl.compare", "cf.compare"):
        body = result["result"]
        total = body["revenue"]["total"] if key == "pl.compare" else body["cash_in"]
        assert total == {"actual": 0, "comparison": 0, "change": 0, "change_pct": None}
    elif key == "risk.sensitivity":
        assert result["result"]["scenarios"][0]["break_even"]["surplus_milk_price_c"] is None
        assert [s["name"] for s in result["result"]["scenarios"]] == ["base"]
    elif key == "kpi.summary":
        assert result["result"]["per_litre_c"]["costs"] is None
        assert result["result"]["per_cow"]["surplus"] is None
        assert result["result"]["dscr"] is None


def _missing_required_cases() -> list[tuple[str, str, dict]]:
    cases: list[tuple[str, str, dict]] = []
    for key in FUNCTION_KEYS:
        required = REQUIRED_FIELDS[key]
        if not required:
            continue
        base = _required_only_payload(key)
        for field in required:
            payload = {k: v for k, v in base.items() if k != field}
            cases.append((key, field, payload))
    return cases


@pytest.mark.parametrize("key,field,payload", _missing_required_cases())
def test_missing_each_required_field(key: str, field: str, payload: dict) -> None:
    result = run_function(key, payload)
    assert result["status"] == "needs_input"
    assert result["function"] == key
    assert missing_field_entry(field) in result["missing"]
    assert result["missing"] == [
        missing_field_entry(f) for f in REQUIRED_FIELDS[key] if f not in payload
    ]
    for item in result["missing"]:
        assert item["unit"] == missing_field_entry(item["field"])["unit"]


def _assert_unknown_field_error(result: dict, *fields: str) -> None:
    assert result["status"] == "error"
    assert result["message"] == "One or more values are invalid."
    assert [item["field"] for item in result["errors"]] == sorted(fields)
    assert all(item["code"] == "unknown_field" for item in result["errors"])
    assert result["error"] == result["errors"][0]


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_extra_unknown_fields_rejected(key: str) -> None:
    payload = {**_happy_payload(key), "not_a_real_field": 999, "farm_id": "demo"}
    result = run_function(key, payload)
    _assert_unknown_field_error(result, "farm_id", "not_a_real_field")


def test_revenue_milk_valid_payload_unchanged() -> None:
    result = run_function("revenue.milk", SAMPLE_MILK)
    _assert_ok_money(result, 200_000)


def test_revenue_milk_missing_milk_price_needs_input() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert result["status"] == "needs_input"
    assert result["missing"] == [missing_field_entry("milk_price")]


def test_revenue_milk_typo_field_is_error() -> None:
    result = run_function(
        "revenue.milk",
        {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_prcie": 0.40,
        },
    )
    _assert_unknown_field_error(result, "milk_prcie")


def test_revenue_milk_random_field_is_error() -> None:
    result = run_function("revenue.milk", {**SAMPLE_MILK, "random_field": 1})
    _assert_unknown_field_error(result, "random_field")


def test_revenue_milk_rejects_field_from_wrong_contract() -> None:
    result = run_function("revenue.milk", {**SAMPLE_MILK, "feed": 80_000})
    _assert_unknown_field_error(result, "feed")


def test_pl_summary_unknown_cost_is_error() -> None:
    result = run_function("pl.summary", {**load_sample_inputs(), "unknown_cost": 1})
    _assert_unknown_field_error(result, "unknown_cost")


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_empty_body(key: str) -> None:
    result = run_function(key, {})
    required = REQUIRED_FIELDS[key]
    if required:
        assert result["status"] == "needs_input"
        assert result["missing"] == [missing_field_entry(f) for f in required]
        assert result["provided"] == []
    elif key == "decision.partial_budget":
        assert result["status"] == "ok"
        assert result["result"]["net_change"] == 0
    else:
        assert result["status"] == "ok"
        _assert_ok_money(result, 0)


def test_registry_maps_are_complete() -> None:
    keys = set(FUNCTIONS)
    assert keys == set(REQUIRED_FIELDS)
    assert keys == set(OPTIONAL_FIELDS)
    assert keys == set(INPUT_MODELS)
    for key in keys:
        spec = FUNCTIONS[key]
        assert spec.id == key
        assert spec.required == REQUIRED_FIELDS[key]
        assert spec.optional == OPTIONAL_FIELDS[key]
        assert spec.input_model is INPUT_MODELS[key]


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_http_smoke_matches_runner(key: str) -> None:
    payload = _happy_payload(key)
    via_runner = run_function(key, payload)
    response = client.post(f"/v1/functions/{key}/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == via_runner["status"]
    assert body["status"] == "ok"
    assert body["result"] == via_runner["result"]


def test_openapi_lists_every_registered_function_route() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for key in FUNCTION_KEYS:
        assert f"/v1/functions/{key}/run" in paths
    assert "/v1/functions/{name}/run" not in paths
