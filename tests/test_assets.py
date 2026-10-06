"""assets.schedule (ADR-0037): depreciation and the fixed asset note.

Register, period Jan–Dec 2026:
  Shed      €240,000 Jan 2022, straight line 20 years → €1,000/month:
            opening (48 months) 192,000 − 12,000 = 180,000
  Tractor   €120,000 Mar 2024, reducing balance 15%/year:
            opening 120,000 × 0.85^(22/12) = 89,080.49; 2026 charge = 15% of it
  Mower     €12,000 Jul 2026, 5 years, residual €2,000 → €166.67/month × 6 = 1,000
  Trailer   €5,000 Feb 2027 → not held in 2026
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

SHED = {"category": "buildings", "cost": 240_000, "year": 2022, "month": 1, "life_months": 240}
TRACTOR = {"cost": 120_000, "year": 2024, "month": 3, "method": "reducing_balance", "annual_rate": 0.15}
MOWER = {"cost": 12_000, "year": 2026, "month": 7, "life_months": 60, "residual_value": 2_000}
TRAILER = {"category": "other", "cost": 5_000, "year": 2027, "month": 2, "life_months": 12}
YEAR = {"from_year": 2026, "from_month": 1, "to_year": 2026, "to_month": 12}


def _run(assets, **period):
    return run_function("assets.schedule", {"assets": assets, **{**YEAR, **period}})


def test_reference_register():
    body = _run([SHED, TRACTOR, MOWER, TRAILER])["result"]
    shed, tractor, mower, trailer = body["assets"]
    assert shed == {
        "category": "buildings", "opening_nbv": 192_000, "additions": 0, "depreciation": 12_000, "closing_nbv": 180_000
    }
    assert tractor["opening_nbv"] == 89_080.49
    assert tractor["depreciation"] == round(0.15 * 89_080.49, 2)
    assert mower == {
        "category": "machinery", "opening_nbv": 0, "additions": 12_000, "depreciation": 1_000, "closing_nbv": 11_000
    }
    assert trailer["closing_nbv"] == 0 and trailer["additions"] == 0
    assert body["by_category"]["machinery"]["additions"] == 12_000
    assert body["by_category"]["other"]["closing_nbv"] == 0


def test_every_note_reconciles():
    body = _run([SHED, TRACTOR, MOWER, TRAILER])["result"]
    for note in [*body["assets"], *body["by_category"].values(), body["total"]]:
        assert round(note["opening_nbv"] + note["additions"] - note["depreciation"], 2) == note["closing_nbv"]


def test_straight_line_stops_at_residual():
    old = {"cost": 10_000, "year": 2010, "month": 1, "life_months": 60, "residual_value": 1_000}
    note = _run([old])["result"]["assets"][0]
    assert (note["opening_nbv"], note["depreciation"], note["closing_nbv"]) == (1_000, 0, 1_000)


def test_consecutive_periods_chain():
    h1 = _run([TRACTOR], to_month=6)["result"]["total"]
    h2 = _run([TRACTOR], from_month=7)["result"]["total"]
    full = _run([TRACTOR])["result"]["total"]
    assert h2["opening_nbv"] == h1["closing_nbv"]
    assert round(h1["depreciation"] + h2["depreciation"], 2) == full["depreciation"]


def test_method_fields_and_period_errors():
    missing = _run([{"cost": 1, "year": 2026, "month": 1}])
    assert missing["error"]["details"]["reason"] == "method_needs_field"
    assert missing["error"]["field"] == "life_months"
    residual = _run([{**MOWER, "residual_value": 20_000}])
    assert residual["error"]["details"]["reason"] == "residual_above_cost"
    backwards = _run([SHED], from_year=2027)
    assert backwards["error"]["details"]["reason"] == "period_reversed"


def test_http_matches_runner():
    payload = {"assets": [SHED, TRACTOR], **YEAR}
    body = client.post("/v1/functions/assets.schedule/run", json=payload).json()
    assert body == run_function("assets.schedule", payload)
