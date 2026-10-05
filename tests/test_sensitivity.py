"""risk.sensitivity (ADR-0029): what-if scenarios and milk-price break-evens.

Hand-checkable quarter (Jan–Mar), 40,000 L/month at €0.40:
  P&L per month: revenue 16,000, costs 14,000 (feed 10,000, labour 4,000), repayments 1,500
  → surplus 6,000 over 120,000 L → surplus break-even 40 − 6,000/120,000 = 35 c/L.
  Cash per month: milk 16,000 in, 14,000 costs + 1,500 loan out → net +500.
  Opening −1,000 → closing −500, 0, +500. Jan needs 500 / 40,000 L = +1.25 c/L
  → cash break-even 41.25 c/L.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.sensitivity import min_shift_all_non_negative
from farm_functions.runner import run_function

client = TestClient(app)

PL = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 10_000, "labour": 4_000, "loan_repayments": 1_500}
    for m in (1, 2, 3)
]
CF = [
    {"year": 2026, "month": m, "milk": 16_000, "feed": 10_000, "labour": 4_000, "interest_paid": 300, "loan_principal_repayments": 1_200}
    for m in (1, 2, 3)
]


def _run(scenarios=(), opening=-1_000, pl=PL, cf=CF):
    return run_function(
        "risk.sensitivity",
        {"pl_months": pl, "cf_months": cf, "opening_cash": opening, "scenarios": list(scenarios)},
    )


def test_base_and_break_evens():
    body = _run()["result"]
    assert body["milk_price_c"] == 40
    assert body["break_even"] == {"surplus_milk_price_c": 35, "cash_milk_price_c": 41.25}
    base = body["scenarios"][0]
    assert base["name"] == "base"
    assert (base["surplus"], base["dscr"], base["closing_cash"]) == (6_000, 1.33, 500)
    assert base["lowest_cash"] == {"period": {"kind": "month", "year": 2026, "month": 1}, "amount": -500}
    assert base["overdraft_months"] == 1


def test_break_evens_are_exact():
    """Running the scenario at each break-even lands on 0."""
    at_surplus = _run([{"milk_price_c": -5}])["result"]["scenarios"][1]
    assert at_surplus["surplus"] == 0
    at_cash = _run([{"milk_price_c": 1.25}])["result"]["scenarios"][1]
    assert at_cash["lowest_cash"]["amount"] == 0
    assert at_cash["overdraft_months"] == 0


def test_milk_price_scales_cash_milk_cheques():
    scenario = _run([{"milk_price_c": -4}])["result"]["scenarios"][1]
    # −4 c/L on 40 c/L = −10% on each 16,000 cheque → −4,800 over the quarter.
    assert scenario["closing_cash"] == 500 - 4_800
    assert scenario["surplus"] == 6_000 - 4_800


def test_volume_and_line_shocks_hit_pl_and_cash():
    scenario = _run([{"name": "dry summer", "milk_volume_pct": -10, "lines_pct": {"feed": 10}}])
    s = scenario["result"]["scenarios"][1]
    # milk −1,600/month, feed +1,000/month → −2,600/month on both statements.
    assert s["name"] == "dry summer"
    assert s["surplus"] == 6_000 - 7_800
    assert s["closing_cash"] == 500 - 7_800


def test_unnamed_scenarios_get_numbered_names():
    names = [s["name"] for s in _run([{}, {"name": "b"}])["result"]["scenarios"]]
    assert names == ["base", "scenario 1", "b"]


def test_no_milk_means_no_break_even():
    pl = [{**m, "milk_litres": 0} for m in PL]
    cf = [{**m, "milk": 0} for m in CF]
    body = _run(pl=pl, cf=cf)["result"]
    assert body["break_even"] == {"surplus_milk_price_c": None, "cash_milk_price_c": None}


def test_rescue_impossible_before_any_milk():
    assert min_shift_all_non_negative([-100, 50], [0, 10]) is None
    assert min_shift_all_non_negative([-100, 50], [20, 10]) == 5


def test_bad_shocks_are_errors():
    assert _run([{"lines_pct": {"milk": 5}}])["error"]["code"] == "unknown_field"
    assert _run([{"lines_pct": {"feed": -150}}])["error"]["details"] == {"minimum": -100}
    assert _run([{"name": 123}])["status"] == "error"


def test_list_shape_errors_do_not_crash():
    """Regression: empty / oversized nested lists map to error, not a crash."""
    assert _run([{}] * 21)["status"] == "error"
    assert run_function("loan.schedule", {"loans": []})["status"] == "error"
    assert run_function("pl.forecast", {"history": [], "forecast": []})["status"] == "error"


def test_http_matches_runner():
    payload = {"pl_months": PL, "cf_months": CF, "opening_cash": 0, "scenarios": [{"milk_price_c": -5}]}
    body = client.post("/v1/functions/risk.sensitivity/run", json=payload).json()
    assert body == run_function("risk.sensitivity", payload)
