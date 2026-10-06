"""risk.tornado (ADR-0044): one driver at a time, ranked by swing.

Quarter, per month: 40,000 L at €0.40 = 16,000; feed 8,000 (variable);
labour 3,000 (fixed); BISS 500; drawings 2,000 (cash only).
±10%: milk price ±4c × 120,000 L = ±4,800 (swing 9,600)
      herd ±10%: milk ±4,800, feed ∓2,400 → ±2,400 (swing 4,800)
      feed ±2,400 (4,800); labour ±900 (1,800); BISS ±150 (300)
      drawings: surplus 0, cash ±600 (1,200)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

PL = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000, "labour": 3_000, "biss": 500}
    for m in (1, 2, 3)
]
CF = [
    {"year": 2026, "month": m, "milk": 16_000, "feed": 8_000, "labour": 3_000, "biss": 500, "household_drawings": 2_000}
    for m in (1, 2, 3)
]
BASE = {"pl_months": PL, "cf_months": CF, "opening_cash": 0}


def _tornado(**extra):
    return run_function("risk.tornado", {**BASE, **extra})["result"]


def _swings(body, key="surplus"):
    return {d["driver"]: d["swing"][key] for d in body["drivers"]}


def test_ranked_by_surplus_swing():
    body = _tornado()
    assert [d["driver"] for d in body["drivers"]][:2] == ["milk_price", "milk_volume"]
    assert _swings(body) == {
        "milk_price": 9_600, "milk_volume": 9_600, "herd_size": 4_800, "feed": 4_800,
        "labour": 1_800, "biss": 300, "household_drawings": 0,
    }
    price = body["drivers"][0]
    assert (price["low_change"], price["high_change"]) == (-4, 4)
    assert price["low"]["surplus"] == body["base"]["surplus"] - 4_800


def test_rank_by_cash_moves_drawings_up():
    body = _tornado(rank_by="closing_cash")
    assert _swings(body, "closing_cash")["household_drawings"] == 1_200
    order = [d["driver"] for d in body["drivers"]]
    assert order.index("household_drawings") < order.index("biss")
    assert [d["driver"] for d in _tornado()["drivers"]][-1] == "household_drawings"


def test_only_lines_with_amounts_appear():
    drivers = {d["driver"] for d in _tornado()["drivers"]}
    assert "vet" not in drivers and "interest_rate" not in drivers


def test_interest_rate_only_with_variable_loans():
    loan = {"balance": 120_000, "annual_rate": 0.05, "remaining_months": 120, "year": 2026, "month": 1}
    assert "interest_rate" not in {d["driver"] for d in _tornado(loans=[loan])["drivers"]}
    body = _tornado(loans=[{**loan, "variable": True}], rate_step_pp=2)
    rate = next(d for d in body["drivers"] if d["driver"] == "interest_rate")
    assert (rate["low_change"], rate["high_change"]) == (-2, 2)
    assert rate["swing"]["surplus"] == 0 and rate["swing"]["closing_cash"] > 0


def test_step_size():
    assert _swings(_tornado(step_pct=20))["milk_price"] == 19_200
    bad = run_function("risk.tornado", {**BASE, "step_pct": 0})
    assert bad["error"]["field"] == "step_pct"


def test_http_matches_runner():
    body = client.post("/v1/functions/risk.tornado/run", json=BASE).json()
    assert body == run_function("risk.tornado", BASE)
