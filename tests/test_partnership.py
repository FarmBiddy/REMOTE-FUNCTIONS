"""tax.partnership (ADR-0053 phase 6): registered / succession farm partnerships.

Hand check, 2026: profit 120,000 after allowances, stock 200,000 → 240,000 (+40,000).
Succession partnership registered 2026 (credit 5,000), both partners single.
  Father 60%: profit 72,000, stock +24,000 × 50% (partnership) = 12,000 → 60,000
    tax as a single farmer on 60,000 = 15,075.32, less credit 60% × 5,000 = 3,000 → 12,075.32
  Son 40%, young trained farmer since 2025: profit 48,000, stock +16,000 × 100% → 32,000
    IT 6,400 − 4,000 − credit 2,000 = 400; USC 60.06 + 333.76 + 3,300 × 3% = 492.82;
    PRSI 32,000 × 4.2375% = 1,356 → 2,248.82
  Partnership 14,324.14
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

FATHER = {"label": "Joe", "profit_share_pct": 60}
SON = {"label": "Mark", "profit_share_pct": 40, "young_trained_farmer_first_year": 2025}
BASE = {
    "tax_year": 2026,
    "trading_profit": 120_000,
    "livestock_opening_value": 200_000,
    "livestock_closing_value": 240_000,
    "partners": [FATHER, SON],
    "succession": {"registered_year": 2026, "successor_birth_year": 1998, "successor": 1},
}


def _run(**overrides):
    return run_function("tax.partnership", {**BASE, **overrides})


def _ok(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]


def _reason(**overrides):
    result = _run(**overrides)
    assert result["status"] == "error"
    return result["errors"][0]["details"]["reason"]


def test_reference_partnership():
    body = _ok()
    father, son = body["partners"]
    assert (father["profit_share"], father["stock_relief_regime"], father["stock_relief"]) == (72_000, "registered_partnership", 12_000)
    assert (father["succession_credit"], father["tax"]["total_tax"]) == (3_000, 12_075.32)
    assert (son["stock_relief_regime"], son["stock_relief"], son["taxable_profit"]) == ("young_trained_farmer", 16_000, 32_000)
    assert (son["succession_credit"], son["tax"]["income_tax"]["net"], son["tax"]["total_tax"]) == (2_000, 400, 2_248.82)
    assert body["total"] == {"stock_relief": 28_000, "succession_credit": 5_000, "total_tax": 14_324.14}
    assert {r["rule_id"] for r in body["rules_applied"]} >= {"stock_relief_rfp", "stock_relief_ytf", "sfp_credit"}


def test_credit_doubles_for_partnerships_registered_from_2027():
    body = _ok(tax_year=2027, succession={"registered_year": 2027, "successor_birth_year": 1998, "successor": 1})
    assert body["succession_credit_total"] == 10_000
    assert [p["succession_credit"] for p in body["partners"]] == [6_000, 4_000]


def test_credit_runs_five_years_and_stops_at_40():
    assert _ok(succession={"registered_year": 2022, "successor_birth_year": 1998, "successor": 1})["succession_credit_total"] == 5_000
    assert _ok(succession={"registered_year": 2021, "successor_birth_year": 1998, "successor": 1})["succession_credit_total"] == 0
    assert _ok(succession={"registered_year": 2026, "successor_birth_year": 1986, "successor": 1})["succession_credit_total"] == 5_000  # 39
    assert _ok(succession={"registered_year": 2026, "successor_birth_year": 1985, "successor": 1})["succession_credit_total"] == 0  # 40


def test_credit_never_exceeds_the_partner_s_profit():
    body = _ok(trading_profit=2_000, livestock_closing_value=200_000)
    assert [p["succession_credit"] for p in body["partners"]] == [1_200, 800]  # profit shares, not 3,000 / 2,000


def test_unregistered_partnership_gets_general_relief():
    body = _ok(registered_partnership=False, succession=None, partners=[FATHER, {**SON, "young_trained_farmer_first_year": None}])
    assert [(p["stock_relief_regime"], p["stock_relief"]) for p in body["partners"]] == [("general", 6_000), ("general", 4_000)]


def test_errors():
    assert _reason(partners=[FATHER, {**SON, "profit_share_pct": 30}]) == "shares_not_100"
    assert _reason(partners=[{**FATHER, "profit_share_pct": 85}, {**SON, "profit_share_pct": 15}]) == "succession_invalid"
    assert _reason(registered_partnership=False) == "succession_invalid"
    assert _reason(tax_year=2028, succession=None) == "rule_not_available"


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.partnership/run", json=BASE).json() == _run()


def test_errors_name_the_partner_field():
    result = _run(partners=[FATHER, {**SON, "spouse_paye_income": 10_000}])
    assert result["errors"][0]["field"] == "partners.1.spouse_paye_income"
    assert _run(tax_year=2028, succession=None)["errors"][0]["field"] == "tax_year"
