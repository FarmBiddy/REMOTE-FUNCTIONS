"""loan.schedule (ADR-0025): state-based annuity amortisation.

Reference: €10,000 at 12% nominal over 12 months → €888.49 per month (standard
annuity table value; monthly rate 1%). First month interest = 10,000 × 1% = €100.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

REFERENCE = {"balance": 10_000, "annual_rate": 0.12, "remaining_months": 12, "year": 2026, "month": 11}


def _schedule(**overrides):
    return run_function("loan.schedule", {"loans": [{**REFERENCE, **overrides}]})


def _loan(**overrides):
    return _schedule(**overrides)["result"]["loans"][0]


def test_reference_annuity():
    body = _loan()
    assert body["monthly_payment"] == 888.49
    first = body["months"][0]
    assert (first["interest"], first["principal"], first["closing_balance"]) == (100, 788.49, 9_211.51)


def test_every_row_reconciles_and_ends_at_zero():
    body = _loan(balance=68_400, annual_rate=0.042, remaining_months=63)
    rows = body["months"]
    for row in rows:
        assert round(row["interest"] + row["principal"], 2) == row["payment"]
        assert round(row["opening_balance"] - row["principal"], 2) == row["closing_balance"]
    for prev, cur in zip(rows, rows[1:]):
        assert cur["opening_balance"] == prev["closing_balance"]
    assert rows[-1]["closing_balance"] == 0
    assert round(sum(r["principal"] for r in rows), 2) == 68_400
    assert body["total_payments"] == round(68_400 + body["total_interest"], 2)


def test_periods_cross_year_boundary():
    periods = [m["period"] for m in _loan()["months"]]
    assert periods[0] == {"kind": "month", "year": 2026, "month": 11}
    assert periods[2] == {"kind": "month", "year": 2027, "month": 1}
    assert periods[-1] == {"kind": "month", "year": 2027, "month": 10}


def test_repaid_pct_from_original_principal():
    assert _loan(original_principal=40_000)["repaid_pct"] == 75
    assert _loan()["repaid_pct"] is None


def test_percent_style_rate_is_rejected():
    result = _schedule(annual_rate=4.2)
    assert result["status"] == "error"
    assert result["error"]["field"] == "annual_rate"
    assert result["error"]["details"] == {"minimum": 0, "maximum": 1}


def test_instalment_count_must_be_whole_and_positive():
    for bad in (0, 12.5, 601):
        result = _schedule(remaining_months=bad)
        assert result["status"] == "error"
        assert result["error"]["field"] == "remaining_months"


def test_original_principal_below_balance_is_rejected():
    result = _schedule(original_principal=5_000)
    assert result["status"] == "error"
    assert result["error"]["details"]["reason"] == "principal_below_balance"


def test_rows_feed_cash_flow_lines():
    """interest / principal plug into cf.monthly without re-deriving anything."""
    row = _schedule()["result"]["months"][0]
    cash = run_function(
        "cf.monthly",
        {
            "year": row["period"]["year"],
            "month": row["period"]["month"],
            "interest_paid": row["interest"],
            "loan_principal_repayments": row["principal"],
        },
    )["result"]
    assert cash["cash_out"] == row["payment"]


def test_portfolio_totals_and_combined_debt_service():
    """Two loans: totals and per-month sums come from the engine, not the UI."""
    second = {"balance": 1_200, "annual_rate": 0, "remaining_months": 2, "year": 2026, "month": 12}
    body = run_function("loan.schedule", {"loans": [REFERENCE, second]})["result"]
    assert [loan["balance"] for loan in body["loans"]] == [10_000, 1_200]
    assert body["total_balance"] == 11_200
    assert body["total_monthly_payment"] == round(888.49 + 600, 2)
    by_month = {(m["period"]["year"], m["period"]["month"]): m for m in body["months"]}
    assert by_month[(2026, 11)]["payment"] == 888.49  # second loan not started yet
    dec = by_month[(2026, 12)]
    assert dec["principal"] == round(body["loans"][0]["months"][1]["principal"] + 600, 2)
    assert dec["payment"] == round(dec["interest"] + dec["principal"], 2)


def test_http_matches_runner():
    payload = {"loans": [REFERENCE]}
    body = client.post("/v1/functions/loan.schedule/run", json=payload).json()
    assert body == run_function("loan.schedule", payload)
