"""tax.company_extraction (ADR-0053 phase 7): paying the director of a farm company.

Hand checks, 2026, single director:
  Mix: 100,000 profit, 40,000 salary, 20,000 dividends
    company: 60,000 × 12.5% = 7,500 → after tax 52,500 − 20,000 dividends = 32,500 kept;
             DWT 25% × 20,000 = 5,000
    director on 60,000: IT 11,200 + USC 1,332.82 + PRSI 2,542.50 = 15,075.32,
             less DWT 5,000 → 10,075.32 due; household keeps 60,000 − 15,075.32 = 44,924.68
    all tax 7,500 + 15,075.32 = 22,575.32 (22.58% of 100,000)
  All salary 100,000: no company tax; IT 8,800 + 56,000 × 40% − 4,000 = 27,200;
    USC 60.06 + 333.76 + 41,344 × 3% + 29,956 × 8% = 4,030.62 (PAYE: no surcharge);
    PRSI 4,237.50 → 35,468.12
  Rent 40,000 kept in the company: CT 10,000; (30,000 × 92.5%) = 27,750 undistributed
    → surcharge 20% = 5,550; with 27,000 dividends the 750 left is under 2,000 → none
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

MIX = {"tax_year": 2026, "trading_profit": 100_000, "salary": 40_000, "dividends": 20_000}


def _ok(**body):
    result = run_function("tax.company_extraction", body)
    assert result["status"] == "ok", result
    return result["result"]


def test_salary_and_dividend_mix():
    body = _ok(**MIX)
    company, director, household = body["company"], body["director"], body["household"]
    assert (company["taxable_trading_profit"], company["corporation_tax"], company["profit_after_tax"]) == (60_000, 7_500, 52_500)
    assert (company["dwt_withheld"], company["close_company_surcharge"], company["retained"]) == (5_000, 0, 32_500)
    assert (director["total_tax"], director["dwt_credit"], director["balance_due"]) == (15_075.32, 5_000, 10_075.32)
    assert household == {"income_after_tax": 44_924.68, "total_tax": 22_575.32, "effective_rate_pct": 22.58}


def test_all_salary():
    body = _ok(tax_year=2026, trading_profit=100_000, salary=100_000)
    assert body["company"]["corporation_tax"] == 0
    assert (body["director"]["income_tax"]["net"], body["director"]["usc"]["farmer"]) == (27_200, 4_030.62)
    assert body["household"]["total_tax"] == 35_468.12


def test_close_company_surcharge_on_undistributed_rent():
    kept = _ok(tax_year=2026, trading_profit=0, non_trading_income=40_000)["company"]
    assert (kept["corporation_tax"], kept["close_company_surcharge"]) == (10_000, 5_550)
    paid = _ok(tax_year=2026, trading_profit=0, non_trading_income=40_000, dividends=27_000)["company"]
    assert paid["close_company_surcharge"] == 0


def test_usc_surcharge_only_on_non_paye_income():
    """170,000 = 50,000 salary + 120,000 dividends: bands give 9,630.62, plus 3% on
    the 20,000 of non-PAYE income above 100,000 = 600."""
    body = _ok(tax_year=2026, trading_profit=300_000, salary=50_000, dividends=120_000)
    assert body["director"]["usc"]["farmer"] == 10_230.62


def test_salary_above_profit_leaves_a_loss_not_negative_tax():
    company = _ok(tax_year=2026, trading_profit=10_000, salary=20_000)["company"]
    assert (company["corporation_tax"], company["profit_after_tax"]) == (0, -10_000)


def test_errors():
    def reason(**body):
        result = run_function("tax.company_extraction", body)
        assert result["status"] == "error"
        return result["errors"][0]["details"]["reason"]

    assert reason(**{**MIX, "tax_year": 2028}) == "rule_not_available"
    assert reason(**MIX, spouse_paye_income=10_000) == "spouse_needs_married"


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.company_extraction/run", json=MIX).json() == run_function(
        "tax.company_extraction", MIX
    )
