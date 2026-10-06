"""pl.net (ADR-0038): Operating Surplus → net profit before tax.

Hand-checkable year: 12 × (16,000 milk − 11,000 costs) = surplus 60,000.
  herd value 300,000 → 310,000 (+10,000); feed stock 8,000 → 5,000 (−3,000)
  adjusted 67,000 − depreciation 12,000 = EBIT 55,000 − interest 4,000 = 51,000
  net margin 51,000 / 192,000 = 26.56%
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

YEAR = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000, "labour": 3_000, "loan_repayments": 1_500}
    for m in range(1, 13)
]
BASE = {
    "months": YEAR,
    "depreciation": 12_000,
    "interest": 4_000,
    "livestock_opening_value": 300_000,
    "livestock_closing_value": 310_000,
    "stock_opening_value": 8_000,
    "stock_closing_value": 5_000,
}


def _net(**overrides):
    return run_function("pl.net", {**BASE, **overrides})


def test_reference_bridge():
    body = _net()["result"]
    assert body["operating_surplus"] == 60_000
    assert (body["livestock_value_change"], body["stock_value_change"]) == (10_000, -3_000)
    assert (body["adjusted_surplus"], body["ebit"], body["net_profit_before_tax"]) == (67_000, 55_000, 51_000)
    assert body["net_margin_pct"] == 26.56


def test_loan_principal_is_not_an_expense():
    """Only interest reduces profit; the 18,000 of repayments stay out."""
    assert _net(interest=0)["result"]["net_profit_before_tax"] == 55_000


def test_falling_herd_value_can_turn_a_surplus_into_a_loss():
    body = _net(livestock_closing_value=200_000)["result"]
    assert body["net_profit_before_tax"] == 51_000 - 110_000


def test_chains_assets_and_loans_outputs():
    """Platform passes engine outputs straight through; no maths in between."""
    assets = run_function(
        "assets.schedule",
        {
            "assets": [{"cost": 144_000, "year": 2026, "month": 1, "life_months": 144}],
            "from_year": 2026, "from_month": 1, "to_year": 2026, "to_month": 12,
        },
    )["result"]
    loans = run_function(
        "loan.schedule",
        {"loans": [{"balance": 50_000, "annual_rate": 0.06, "remaining_months": 60, "year": 2026, "month": 1}]},
    )["result"]
    interest_2026 = sum(m["interest"] for m in loans["months"] if m["period"]["year"] == 2026)
    body = run_function(
        "pl.net",
        {"months": YEAR, "depreciation": assets["total"]["depreciation"], "interest": round(interest_2026, 2)},
    )["result"]
    assert body["depreciation"] == 12_000
    assert body["net_profit_before_tax"] == round(60_000 - 12_000 - interest_2026, 2)


def test_http_matches_runner():
    body = client.post("/v1/functions/pl.net/run", json=BASE).json()
    assert body == run_function("pl.net", BASE)
