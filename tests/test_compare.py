"""pl.compare / cf.compare (ADR-0035): actual vs prior year or budget.

Hand-checkable quarter:
  2026 (actual):     44,000 L/month at €0.38, feed 11,000, labour 4,000
  2025 (comparison): 40,000 L/month at €0.45, feed 10,000, labour 4,000
  Milk: 50,160 vs 54,000 → −3,840 = volume +12,000 L × €0.45 (+5,400)
                                 + price −7c × 132,000 L (−9,240)
  Surplus: 5,160 vs 12,000 → −6,840 (−57%)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)


def _month(year, month, litres, price, feed):
    return {"year": year, "month": month, "milk_litres": litres, "milk_price": price, "feed": feed, "labour": 4_000}


ACTUAL = [_month(2026, m, 44_000, 0.38, 11_000) for m in (1, 2, 3)]
PRIOR = [_month(2025, m, 40_000, 0.45, 10_000) for m in (1, 2, 3)]


def _pl(actual=ACTUAL, comparison=PRIOR):
    return run_function("pl.compare", {"actual": actual, "comparison": comparison})


def test_line_variances():
    body = _pl()["result"]
    assert body["comparison"] == {
        "from": {"kind": "month", "year": 2025, "month": 1},
        "to": {"kind": "month", "year": 2025, "month": 3},
        "month_count": 3,
    }
    assert body["revenue"]["milk"] == {"actual": 50_160, "comparison": 54_000, "change": -3_840, "change_pct": -7.11}
    assert body["costs"]["lines"]["feed"]["change_pct"] == 10
    assert body["costs"]["lines"]["labour"]["change"] == 0
    assert body["profit"]["net"] == {"actual": 5_160, "comparison": 12_000, "change": -6_840, "change_pct": -57}


def test_price_and_volume_effects_add_up():
    body = _pl()["result"]
    milk = body["milk"]
    assert (milk["volume_effect"], milk["price_effect"]) == (5_400, -9_240)
    assert milk["volume_effect"] + milk["price_effect"] == body["revenue"]["milk"]["change"]
    assert milk["price_c"] == {"actual": 38, "comparison": 45, "change": -7}
    assert milk["litres"]["change"] == 12_000


def test_margin_change_matches_published_margins():
    margin = _pl()["result"]["margin_pct"]
    assert margin["change_pp"] == round(margin["actual"] - margin["comparison"], 2)


def test_budget_comparison_can_be_the_same_months():
    budget = [_month(2026, m, 45_000, 0.40, 10_000) for m in (1, 2, 3)]
    body = _pl(comparison=budget)["result"]
    assert body["actual"]["from"] == body["comparison"]["from"]


def test_zero_comparison_gives_null_pct():
    body = _pl(comparison=[{**m, "feed": 0} for m in PRIOR])["result"]
    assert body["costs"]["lines"]["feed"]["change_pct"] is None


def test_duplicate_month_is_rejected():
    assert _pl(actual=[ACTUAL[0], ACTUAL[0]])["error"]["details"]["reason"] == "duplicate_period"


def test_cash_compare_sections_and_totals():
    actual = [{"year": 2026, "month": 1, "milk": 16_000, "feed": 11_000, "household_drawings": 2_000}]
    budget = [{"year": 2026, "month": 1, "milk": 18_000, "feed": 10_000, "household_drawings": 2_500}]
    body = run_function("cf.compare", {"actual": actual, "comparison": budget})["result"]
    assert body["operating"]["net"]["change"] == -3_000
    assert body["financing"]["outflows"]["lines"]["household_drawings"]["change"] == -500
    assert body["net_cash_flow"] == {"actual": 3_000, "comparison": 5_500, "change": -2_500, "change_pct": -45.45}
    assert "closing_cash" not in body


def test_http_matches_runner():
    payload = {"actual": ACTUAL, "comparison": PRIOR}
    body = client.post("/v1/functions/pl.compare/run", json=payload).json()
    assert body == run_function("pl.compare", payload)
