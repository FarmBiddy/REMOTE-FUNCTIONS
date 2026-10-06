"""decision.partial_budget (ADR-0045): rent 20 ha and milk 20 more cows.

  Gains:  milk from 20 extra cows 60,000
  Losses: land rent 10,000 + feed & vet 30,000 + stores no longer sold 4,000 = 44,000
  Operating change 16,000
  Capital 40,000 over 10 years at 5%: depreciation 4,000 + interest 40,000 / 2 × 5% = 1,000
  Net 11,000 a year; payback 40,000 / 16,000 = 2.5 years; ROI (16,000 − 4,000) / 40,000 = 30%
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

EXPANSION = {
    "added_income": [{"label": "milk from 20 extra cows", "amount": 60_000}],
    "added_costs": [
        {"label": "land rent 20 ha", "amount": 10_000},
        {"label": "feed & vet", "amount": 30_000},
    ],
    "reduced_income": [{"label": "cattle no longer sold as stores", "amount": 4_000}],
    "capital": {"amount": 40_000, "life_years": 10, "annual_rate": 0.05},
}


def _budget(**overrides):
    return run_function("decision.partial_budget", {**EXPANSION, **overrides})


def test_reference_expansion():
    body = _budget()["result"]
    assert body["added_costs"]["total"] == 40_000
    assert body["added_costs"]["items"][0] == {"label": "land rent 20 ha", "amount": 10_000}
    assert (body["gains"], body["losses"], body["operating_change"]) == (60_000, 49_000, 16_000)
    assert body["capital"] == {
        "amount": 40_000, "life_years": 10, "annual_rate": 0.05, "depreciation": 4_000,
        "interest": 1_000, "annual_charge": 5_000, "simple_payback_years": 2.5,
        "return_on_investment_pct": 30,
    }
    assert body["net_change"] == 11_000 and body["worthwhile"] is True


def test_no_capital_needed():
    """Contract rearing: pay 12,000 rearing fees, save 15,000 of costs, lose 1,000 sales."""
    body = _budget(
        added_income=[],
        reduced_costs=[{"label": "heifer feed, labour, vet", "amount": 15_000}],
        added_costs=[{"label": "rearing fee", "amount": 12_000}],
        reduced_income=[{"label": "cull sales", "amount": 1_000}],
        capital=None,
    )["result"]
    assert body["capital"] is None
    assert body["net_change"] == 2_000


def test_loss_making_change_has_no_payback():
    body = _budget(added_income=[{"label": "milk", "amount": 40_000}])["result"]
    assert body["operating_change"] == -4_000
    assert body["capital"]["simple_payback_years"] is None
    assert body["worthwhile"] is False


def test_item_validation():
    assert _budget(added_costs=[{"label": "", "amount": 1}])["status"] == "error"
    assert _budget(added_costs=[{"label": "rent", "amount": -1}])["error"]["code"] == "negative_value"
    life = _budget(capital={"amount": 1, "life_years": 0})
    assert life["error"]["field"] == "life_years"


def test_http_matches_runner():
    body = client.post("/v1/functions/decision.partial_budget/run", json=EXPANSION).json()
    assert body == run_function("decision.partial_budget", EXPANSION)
