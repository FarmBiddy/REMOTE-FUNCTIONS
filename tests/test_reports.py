"""report.bank / report.advisor / report.accountant (ADR-0041): one farm file, three bundles.

Reference farm file, reporting period Jan–Sep 2026 (9 months):
  P&L per month: milk 40,000 L × €0.40 = 16,000; feed 8,000; labour 3,000; repayments 1,500
    → surplus 45,000
  Cash per month: milk 16,000 in; feed, labour, interest 300, principal 1,200, drawings 2,000 out
    → net 1,500/month; opening 5,000 → closing 18,500
  Herd 300,000 → 310,000 (+10,000); shed €240,000 Jan 2022 over 20 years → 9,000 for 9 months
  Net profit = 45,000 + 10,000 − 9,000 − interest 2,700 = 43,300
  Projected Oct–Dec: 38,000 L × €0.45 (P&L), cash +2,500/month → 26,000 at Dec
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

PL = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000, "labour": 3_000, "loan_repayments": 1_500}
    for m in range(1, 10)
]
CF = [
    {"year": 2026, "month": m, "milk": 16_000, "feed": 8_000, "labour": 3_000, "interest_paid": 300,
     "loan_principal_repayments": 1_200, "household_drawings": 2_000}
    for m in range(1, 10)
]
PROJ_PL = [
    {"year": 2026, "month": m, "milk_litres": 38_000, "milk_price": 0.45, "feed": 8_000, "labour": 3_000, "loan_repayments": 1_500}
    for m in (10, 11, 12)
]
PROJ_CF = [{**CF[0], "month": m, "milk": 17_000} for m in (10, 11, 12)]
FILE = {
    "pl_months": PL,
    "cf_months": CF,
    "opening_cash": 5_000,
    "milking_cows": 100,
    "hectares": 40,
    "prior_pl_months": [{**m, "year": 2025, "milk_price": 0.45} for m in PL],
    "projected_pl_months": PROJ_PL,
    "projected_cf_months": PROJ_CF,
    "loans": [{"balance": 68_400, "annual_rate": 0.042, "remaining_months": 63, "year": 2026, "month": 10}],
    "assets": [{"category": "buildings", "cost": 240_000, "year": 2022, "month": 1, "life_months": 240}],
    "debtors": 9_000,
    "stock": 5_000,
    "livestock": 310_000,
    "land": 900_000,
    "creditors": 12_490,
    "livestock_opening_value": 300_000,
    "drawings": 18_000,
    "tax": 4_500,
    "scenarios": [{"name": "milk -5c", "milk_price_c": -5}],
}


def _report(kind, **overrides):
    return run_function(f"report.{kind}", {**FILE, **overrides})


def test_bank_report():
    body = _report("bank")["result"]
    assert body["as_of"] == {"kind": "month", "year": 2026, "month": 9}
    assert body["period"]["month_count"] == 9
    assert body["profit"]["net_profit_before_tax"] == 43_300
    assert body["kpis"]["debt"]["balance"] == 68_400
    assert body["loans"]["total_balance"] == 68_400
    assert body["capacity"]["repayment_capacity"] == 45_000 - 18_000 - 4_500
    assert body["capacity"]["new_loan"] is None  # no application in the file
    assert body["cash"]["actual"]["closing_cash"] == 18_500
    assert body["cash"]["projection"]["opening_cash"] == 18_500
    assert body["cash"]["projection"]["closing_cash"] == 18_500 + 3 * 2_500
    assert body["balance_sheet"]["assets"]["current"]["cash"] == 18_500


def test_bank_report_sizes_a_requested_loan():
    terms = {"annual_rate": 0.05, "term_months": 120, "min_cover": 1.1}
    capacity = _report("bank", new_loan=terms)["result"]["capacity"]
    direct = run_function(
        "debt.capacity",
        {"months": PL, "drawings": 18_000, "tax": 4_500, **terms},
    )["result"]
    assert capacity == direct


def test_advisor_report_is_forward_looking_when_projected():
    body = _report("advisor")["result"]
    assert body["comparison"]["milk"]["price_effect"] == -0.05 * 360_000
    sensitivity = body["sensitivity"]
    assert sensitivity["shocks_from"] == {"kind": "month", "year": 2026, "month": 10}
    base, milk = sensitivity["scenarios"]
    assert milk["surplus"] == base["surplus"] - 0.05 * 3 * 38_000


def test_advisor_report_without_projection_or_prior():
    body = _report("advisor", projected_pl_months=[], projected_cf_months=[], prior_pl_months=[])["result"]
    assert body["comparison"] is None
    assert body["sensitivity"]["shocks_from"] is None


def test_accountant_report():
    body = _report("accountant")["result"]
    assert body["profit_and_loss"]["profit"] == {"net": 45_000}
    assert body["profit_and_loss"]["costs"]["lines"]["feed"] == 72_000
    assert body["net_profit"]["depreciation"] == 9_000
    assert body["fixed_assets"]["total"]["closing_nbv"] == body["balance_sheet"]["assets"]["non_current"]["buildings"]
    flow = body["cash_flow"]
    assert (flow["opening_cash"], flow["net_cash_flow"], flow["closing_cash"]) == (5_000, 13_500, 18_500)
    assert flow["financing"]["outflows"]["lines"]["household_drawings"] == 18_000


def test_reports_share_figures():
    bank, accountant = _report("bank")["result"], _report("accountant")["result"]
    assert bank["profit"] == accountant["net_profit"]
    assert bank["balance_sheet"] == accountant["balance_sheet"]


def test_misaligned_and_overlapping_periods_are_rejected():
    short_cash = _report("bank", cf_months=CF[:-1])
    assert short_cash["error"]["details"]["reason"] == "periods_misaligned"
    overlap = _report("bank", projected_cf_months=[CF[-1]])
    assert overlap["error"]["details"]["reason"] == "projection_overlaps_period"


def test_http_matches_runner():
    body = client.post("/v1/functions/report.bank/run", json=FILE).json()
    assert body == run_function("report.bank", FILE)
