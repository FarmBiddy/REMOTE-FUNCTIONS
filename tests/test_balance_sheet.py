"""bs.summary (ADR-0039): balance sheet at month end, net worth and ratios.

Reference, 31 Dec 2026:
  Current assets   cash −4,000 (→ overdraft), debtors 9,000, stock 5,000 = 14,000
  Non-current      land 900,000, shed NBV 180,000 (ADR-0037 reference), livestock 310,000
  Current liab.    overdraft 4,000, creditors 12,490, loan due within 12 months 6,000
  Non-current      loan due after 12 months 6,000 (12,000 at 0% over 24 months)
  Net worth = 1,404,000 − 28,490 = 1,375,510
  Current ratio = 14,000 / 22,490 = 0.62 (livestock excluded)
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

SHED = {"category": "buildings", "cost": 240_000, "year": 2022, "month": 1, "life_months": 240}
LOAN = {"balance": 12_000, "annual_rate": 0, "remaining_months": 24, "year": 2027, "month": 1}
BASE = {
    "year": 2026,
    "month": 12,
    "cash": -4_000,
    "debtors": 9_000,
    "stock": 5_000,
    "livestock": 310_000,
    "land": 900_000,
    "creditors": 12_490,
    "loans": [LOAN],
    "assets": [SHED],
}


def _bs(**overrides):
    return run_function("bs.summary", {**BASE, **overrides})


def test_reference_balance_sheet():
    body = _bs()["result"]
    assert body["assets"]["current"] == {"cash": 0, "debtors": 9_000, "stock": 5_000, "total": 14_000}
    assert body["assets"]["non_current"]["buildings"] == 180_000
    assert body["liabilities"]["current"] == {
        "overdraft": 4_000, "creditors": 12_490, "loans_due_within_12_months": 6_000, "total": 22_490
    }
    assert body["liabilities"]["non_current"]["loans_due_after_12_months"] == 6_000
    assert body["net_worth"] == 1_375_510
    assert body["ratios"] == {
        "equity_pct": 97.97, "debt_to_assets_pct": 2.03, "current_ratio": 0.62, "working_capital": -8_490
    }


def test_matches_assets_and_loan_schedules():
    """Same register and loans give the same NBV and balance as the dedicated IDs."""
    nbv = run_function(
        "assets.schedule",
        {"assets": [SHED], "from_year": 2026, "from_month": 1, "to_year": 2026, "to_month": 12},
    )["result"]["total"]["closing_nbv"]
    loans = run_function("loan.schedule", {"loans": [LOAN]})["result"]
    body = _bs()["result"]
    assert body["assets"]["non_current"]["buildings"] == nbv
    loan_liabilities = (
        body["liabilities"]["current"]["loans_due_within_12_months"]
        + body["liabilities"]["non_current"]["loans_due_after_12_months"]
    )
    assert loan_liabilities == loans["total_balance"]


def test_assets_bought_after_the_date_are_excluded():
    later = {"cost": 50_000, "year": 2027, "month": 3, "life_months": 60}
    assert _bs(assets=[SHED, later])["result"]["assets"]["non_current"]["machinery"] == 0


def test_totals_balance():
    body = _bs()["result"]
    assert body["assets"]["total"] == body["liabilities"]["total"] + body["net_worth"]


def test_no_liabilities_gives_null_current_ratio():
    body = _bs(cash=1_000, creditors=0, loans=[])["result"]
    assert body["ratios"]["current_ratio"] is None
    assert body["ratios"]["debt_to_assets_pct"] == 0


def test_http_matches_runner():
    body = client.post("/v1/functions/bs.summary/run", json=BASE).json()
    assert body == run_function("bs.summary", BASE)
