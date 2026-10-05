"""debt.capacity (ADR-0036): repayment capacity and the largest affordable loan.

Hand-checkable year: 12 × (16,000 milk − 11,000 costs) = surplus 60,000,
loan repayments 12 × 1,500 = 18,000, drawings 24,000, tax 6,000.
  capacity = 60,000 − 24,000 − 6,000 = 30,000 → cover 30,000 / 18,000 = 1.67
  bank asks 1.25 cover: 30,000 / 1.25 = 24,000 → headroom 6,000/yr = 500/month
  500/month over 10 years at 5% → €47,140.67 (standard annuity factor 94.2814)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.loans import annuity_payment, annuity_principal
from farm_functions.runner import run_function

client = TestClient(app)

YEAR = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000, "labour": 3_000, "loan_repayments": 1_500}
    for m in range(1, 13)
]
BASE = {"months": YEAR, "annual_rate": 0.05, "term_months": 120, "drawings": 24_000, "tax": 6_000, "min_cover": 1.25}


def _run(**overrides):
    return run_function("debt.capacity", {**BASE, **overrides})


def test_reference_year():
    body = _run()["result"]
    assert (body["surplus"], body["repayment_capacity"], body["debt_service"]) == (60_000, 30_000, 18_000)
    assert body["repayment_cover"] == 1.67
    assert body["new_loan"]["max_monthly_payment"] == 500
    assert body["new_loan"]["max_principal"] == 47_140.67
    assert body["new_loan"]["monthly_payment_at_max"] <= 500


def test_inverse_annuity_round_trips():
    principal = annuity_principal(500, 0.05, 120)
    assert round(annuity_payment(principal, 0.05, 120), 6) == 500
    assert annuity_principal(100, 0, 12) == 1_200


def test_off_farm_income_adds_capacity():
    body = _run(off_farm_income=6_000)["result"]
    assert body["repayment_capacity"] == 36_000
    assert body["new_loan"]["max_monthly_payment"] == 900  # (36,000 / 1.25 − 18,000) / 12


def test_no_headroom_means_no_new_loan():
    body = _run(drawings=40_000)["result"]
    assert body["repayment_capacity"] == 14_000
    assert body["new_loan"]["max_principal"] == 0


def test_no_existing_debt_gives_null_cover():
    body = _run(months=[{**m, "loan_repayments": 0} for m in YEAR])["result"]
    assert body["repayment_cover"] is None
    assert body["new_loan"]["max_monthly_payment"] == 2_000  # 30,000 / 1.25 / 12


def test_cover_below_one_is_rejected():
    result = _run(min_cover=0.9)
    assert result["error"]["field"] == "min_cover"
    assert result["error"]["details"] == {"minimum": 1}


def test_http_matches_runner():
    body = client.post("/v1/functions/debt.capacity/run", json=BASE).json()
    assert body == run_function("debt.capacity", BASE)
