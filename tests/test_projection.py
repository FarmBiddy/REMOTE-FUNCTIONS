"""plan.projection (ADR-0042): multi-year annual projection.

Base Oct 2025 – Sep 2026: 12 × (40,000 L at €0.40, feed 8,000, labour 3,000)
  → 480,000 L, revenue 192,000, costs 132,000, surplus 60,000.
Existing loan €60,000 at 0% over 60 months from Oct 2026 → 12,000 a year.
Investment in year 2: €50,000 machine (10 years), fully financed at 0% over
100 months (first instalment month 2 of year 2), saving €6,000 labour a year
from year 3.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.growth import carry_forward, compound_indexes
from farm_functions.runner import run_function

client = TestClient(app)

BASE = [
    {"year": 2025 if m >= 10 else 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000, "labour": 3_000}
    for m in [10, 11, 12, *range(1, 10)]
]
LOAN = {"balance": 60_000, "annual_rate": 0, "remaining_months": 60, "year": 2026, "month": 10}
MACHINE = {
    "year": 2, "amount": 50_000, "life_months": 120,
    "loan": {"amount": 50_000, "annual_rate": 0, "remaining_months": 100},
    "annual_effects": {"labour": -6_000},
}
PLAN = {"base_pl_months": BASE, "opening_cash": 10_000, "milking_cows": 100, "years": 3}


def _plan(**overrides):
    return run_function("plan.projection", {**PLAN, **overrides})


def test_no_assumptions_means_nothing_changes():
    body = _plan()["result"]
    assert body["base"]["milk_litres"] == 480_000 and body["base"]["milk_price_c"] == 40
    for year in body["years"]:
        assert year["pl"]["operating_surplus"] == 60_000
        assert year["assumptions_used"]["milk_price"] == 0.40
    assert [y["cash"]["closing"] for y in body["years"]] == [70_000, 130_000, 190_000]
    assert body["years"][0]["period"]["from"] == {"kind": "month", "year": 2026, "month": 10}


def test_price_herd_and_inflation_paths():
    """Y1: 480,000 L × 0.42 − 132,000 × 1.03 = 65,640.
    Y2: herd +10% → 528,000 L × 0.40 (carried) − (96,000 × 1.1 + 36,000) × 1.03² = 60,976.56."""
    body = _plan(assumptions={"milk_price": [0.42, 0.40], "herd_pct": [0, 10], "cost_inflation_pct": [3, 3, 3]})["result"]
    y1, y2, y3 = body["years"]
    assert y1["pl"]["operating_surplus"] == 65_640
    assert y2["pl"]["milk_litres"] == 528_000
    assert y2["pl"]["operating_surplus"] == 60_976.56
    assert y3["assumptions_used"]["milk_price"] == 0.40
    assert y2["kpis"]["milking_cows"] == 110


def test_line_inflation_and_amount_overrides():
    body = _plan(
        assumptions={"cost_inflation_pct": [3], "lines_inflation_pct": {"feed": [10]}, "lines_amount": {"biss": [20_000]}}
    )["result"]
    y1 = body["years"][0]
    assert y1["pl"]["costs"]["lines"]["feed"] == 105_600
    assert y1["pl"]["costs"]["lines"]["labour"] == 37_080
    assert y1["pl"]["revenue"]["schemes"] == 20_000
    assert body["years"][2]["pl"]["revenue"]["schemes"] == 20_000  # carried forward


def test_loans_and_financed_investment():
    body = _plan(loans=[LOAN], investments=[MACHINE])["result"]
    y1, y2, y3 = body["years"]
    assert [y["debt"]["closing_balance"] for y in body["years"]] == [48_000, 80_500, 62_500]
    assert (y1["debt"]["debt_service"], y2["debt"]["debt_service"], y3["debt"]["debt_service"]) == (12_000, 17_500, 18_000)
    assert (y2["cash"]["capex"], y2["cash"]["new_loans"]) == (50_000, 50_000)
    assert y1["pl"]["depreciation"] == 0 and y2["pl"]["depreciation"] == 5_000
    assert y3["pl"]["costs"]["lines"]["labour"] == 36_000 - 6_000
    assert y2["balance_sheet"]["fixed_assets"] == 45_000


def test_cash_and_net_worth_roll():
    body = _plan(loans=[LOAN], assumptions={"drawings": [30_000], "tax": [5_000]}, land=500_000, livestock=200_000)["result"]
    for prev, cur in zip(body["years"], body["years"][1:]):
        assert cur["cash"]["opening"] == prev["cash"]["closing"]
    y1 = body["years"][0]
    assert y1["cash"]["net"] == 60_000 - 30_000 - 5_000 - 12_000
    assert y1["debt"]["repayment_cover"] == round((60_000 - 35_000) / 12_000, 2)
    sheet = y1["balance_sheet"]
    assert sheet["net_worth"] == sheet["cash"] + sheet["fixed_assets"] + sheet["land"] + sheet["livestock"] - sheet["debt"]


def test_flags():
    body = _plan(loans=[LOAN], assumptions={"milk_price": [0.30], "drawings": [40_000]}, min_cover=1.25)["result"]
    y1 = body["years"][0]
    # 480,000 × 0.30 − 132,000 = 12,000 surplus; DSCR 1.0 < 1.25; cash 10,000 + 12,000 − 40,000 − 12,000 < 0
    assert y1["debt"]["dscr"] == 1
    assert y1["flags"] == {"negative_cash": True, "below_min_cover": True}
    assert _plan()["result"]["years"][0]["flags"]["below_min_cover"] is None


def test_growth_helpers():
    assert compound_indexes([10, 0, 5], 4) == [1.1, 1.1, 1.1 * 1.05, 1.1 * 1.05]
    assert carry_forward([1, 2], 4, 0) == [1, 2, 2, 2]
    assert carry_forward([], 2, 9) == [9, 9]


def test_input_errors():
    assert _plan(base_pl_months=BASE[:11])["status"] == "error"
    gap = [*BASE[:11], {**BASE[11], "year": 2027}]
    assert _plan(base_pl_months=gap)["error"]["details"]["reason"] == "base_not_12_consecutive"
    too_long = _plan(assumptions={"milk_price": [0.4] * 4})
    assert too_long["error"]["details"]["reason"] == "assumption_longer_than_years"
    late = _plan(investments=[{**MACHINE, "year": 3}], years=2)
    assert late["error"]["details"]["reason"] == "investment_outside_years"
    assert _plan(years=11)["error"]["details"] == {"minimum": 1, "maximum": 10}
    assert _plan(assumptions={"lines_inflation_pct": {"milk": [1]}})["error"]["code"] == "unknown_field"


def test_http_matches_runner():
    payload = {**PLAN, "loans": [LOAN], "investments": [MACHINE]}
    body = client.post("/v1/functions/plan.projection/run", json=payload).json()
    assert body == run_function("plan.projection", payload)
