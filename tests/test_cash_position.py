"""P3.4 cash position: opening + net = closing, rolled across consecutive months.

Hand-checkable Jan–Mar 2026 (opening €5,000; spring calving, no milk in Jan):

  Jan: in 2000 (biss)            out 9000 (feed 6000, labour 3000)  net -7000  close  -2000
  Feb: in 4000 (milk)            out 5000 (feed)                    net -1000  close  -3000
  Mar: in 18000 (milk)           out 5500 (feed 5000, interest 500) net 12500  close   9500
  Period: in 24000  out 19500  net 4500  closing 9500 (= 5000 + 4500)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

JAN = {"year": 2026, "month": 1, "biss": 2_000, "feed": 6_000, "labour": 3_000}
FEB = {"year": 2026, "month": 2, "milk": 4_000, "feed": 5_000}
MAR = {"year": 2026, "month": 3, "milk": 18_000, "feed": 5_000, "interest_paid": 500}


def _months(*months, opening=5_000):
    return run_function("cf.months", {"opening_cash": opening, "months": list(months)})


def test_roll_forward_reference_quarter():
    body = _months(MAR, JAN, FEB)["result"]  # input order does not matter
    assert [m["period"]["month"] for m in body["months"]] == [1, 2, 3]
    assert [m["opening_cash"] for m in body["months"]] == [5_000, -2_000, -3_000]
    assert [m["closing_cash"] for m in body["months"]] == [-2_000, -3_000, 9_500]
    assert (body["cash_in"], body["cash_out"], body["net_cash_flow"]) == (24_000, 19_500, 4_500)
    assert body["opening_cash"] == 5_000
    assert body["closing_cash"] == 9_500


def test_every_month_reconciles_to_the_cent():
    body = _months(
        {"year": 2026, "month": 1, "milk": 0.105, "feed": 0.004},
        {"year": 2026, "month": 2, "milk": 1_000.555},
        opening=0.015,
    )["result"]
    for m in body["months"]:
        assert round(m["opening_cash"] + m["net_cash_flow"], 2) == m["closing_cash"]
    for prev, cur in zip(body["months"], body["months"][1:]):
        assert cur["opening_cash"] == prev["closing_cash"]


def test_year_boundary_is_consecutive():
    result = _months({"year": 2025, "month": 12}, {"year": 2026, "month": 1})
    assert result["status"] == "ok"


def test_gap_is_rejected_with_reason():
    result = _months(JAN, MAR)
    assert result["status"] == "error"
    assert result["errors"][0]["details"]["reason"] == "non_contiguous_months"


def test_duplicate_month_is_rejected():
    result = _months(JAN, JAN)
    assert result["status"] == "error"
    assert result["errors"][0]["details"]["reason"] == "duplicate_period"


def test_opening_cash_required_and_may_be_negative():
    missing = run_function("cf.months", {"months": [JAN]})
    assert missing["status"] == "needs_input"
    assert missing["missing"] == [{"field": "opening_cash", "unit": "EUR"}]

    overdraft = _months(JAN, opening=-10_000)["result"]
    assert overdraft["closing_cash"] == -17_000


def test_cash_lines_stay_non_negative():
    result = _months({"year": 2026, "month": 1, "feed": -1})
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "negative_value"


def test_cf_monthly_optional_opening_cash():
    without = run_function("cf.monthly", MAR)["result"]
    assert without["opening_cash"] is None and without["closing_cash"] is None
    with_opening = run_function("cf.monthly", {**MAR, "opening_cash": -3_000})["result"]
    assert with_opening["closing_cash"] == 9_500


def test_cf_months_http_matches_runner():
    payload = {"opening_cash": 5_000, "months": [JAN, FEB, MAR]}
    body = client.post("/v1/functions/cf.months/run", json=payload).json()
    assert body == run_function("cf.months", payload)
