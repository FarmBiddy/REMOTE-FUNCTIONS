"""tax.estimate (ADR-0053): Irish tax for one year on taxable farming profit.

Hand checks, tax year 2026:
  Single, 60,000 profit
    IT   44,000 × 20% + 16,000 × 40% = 15,200 − credits (personal 2,000 + earned 2,000) = 11,200
    USC  12,012 × 0.5% = 60.06 + 16,688 × 2% = 333.76 + 31,300 × 3% = 939.00 → 1,332.82
    PRSI 60,000 × 4.2375% (4.2% Jan–Sep, 4.35% Oct–Dec) = 2,542.50
    total 15,075.32
  Married (joint), 60,000 profit + spouse PAYE 30,000
    band 53,000 + min(35,000, 30,000) = 83,000; IT 16,600 + 7,000 × 40% = 19,400
    − credits (married 4,000 + earned 2,000 + employee 2,000) = 11,400
    USC farmer 1,332.82 + spouse (60.06 + 333.76 + 1,300 × 3%) 432.82; PRSI spouse 1,271.25
    total 11,400 + 1,765.64 + 3,813.75 = 16,979.39
  Company, 100,000 trading + 10,000 rent: 12,500 + 2,500 = 15,000
"""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)

SINGLE = {"business_type": "sole_trader", "tax_year": 2026, "taxable_profit": 60_000, "income_averaging": False}


def _run(**body):
    return run_function("tax.estimate", body)


def _ok(**body):
    result = _run(**body)
    assert result["status"] == "ok", result
    return result["result"]


def _reason(**body):
    result = _run(**body)
    assert result["status"] == "error"
    return result["errors"][0]["details"]["reason"]


def test_single_farmer():
    body = _ok(**SINGLE)
    assert body["assessment"] == "single"
    assert (body["income_tax"]["gross"], body["income_tax"]["credits"], body["income_tax"]["net"]) == (15_200, 4_000, 11_200)
    assert body["usc"] == {"farmer": 1_332.82, "spouse": 0, "total": 1_332.82}
    assert body["prsi"] == {"farmer": 2_542.5, "spouse": 0, "total": 2_542.5}
    assert (body["total_tax"], body["effective_rate_pct"]) == (15_075.32, 25.13)
    assert body["corporation_tax"] is None and body["stock_relief_cap"] is None


def test_joint_assessment_shares_the_band():
    body = _ok(**SINGLE, marital_status="married", spouse_paye_income=30_000)
    assert body["assessment"] == "joint"
    assert body["income_tax"]["standard_rate_band"] == 83_000
    assert body["income_tax"]["net"] == 11_400
    assert body["usc"]["spouse"] == 432.82 and body["prsi"]["spouse"] == 1_271.25
    assert body["total_tax"] == 16_979.39
    # One income: the band increase is limited by the spouse's income (none).
    assert _ok(**SINGLE, marital_status="married")["income_tax"]["standard_rate_band"] == 53_000


def test_low_income_pays_only_the_prsi_minimum():
    body = _ok(**{**SINGLE, "taxable_profit": 12_000})
    assert (body["income_tax"]["net"], body["usc"]["total"], body["prsi"]["total"]) == (0, 0, 650)


def test_loss_is_nil_income():
    body = _ok(**{**SINGLE, "taxable_profit": -20_000}, other_income=0)
    assert body["total_tax"] == 0 and body["income"]["total"] == 0


def test_company_pays_corporation_tax():
    body = _ok(business_type="company", tax_year=2026, taxable_profit=100_000, other_income=10_000)
    assert body["corporation_tax"] == {"trading": 12_500, "non_trading": 2_500, "total": 15_000}
    assert body["income_tax"] is None and body["total_tax"] == 15_000
    assert [r["rule_id"] for r in body["rules_applied"]] == ["ct_rate_trading", "ct_rate_non_trading"]


def test_young_trained_farmer_cap_on_tax_saved():
    """150,000 after 100,000 relief: the relief saves 40% IT + 8% USC + 3% surcharge
    = 51,000, above the 40,000 yearly cap → 11,000 back. With 70,000 of lifetime aid
    used, only 30,000 is left → 21,000 back."""
    body = _ok(**{**SINGLE, "taxable_profit": 150_000}, stock_relief=100_000, stock_relief_regime="young_trained_farmer")
    cap = body["stock_relief_cap"]
    assert (cap["tax_value"], cap["cap"], cap["clawback"]) == (51_000, 40_000, 11_000)
    plain = _ok(**{**SINGLE, "taxable_profit": 150_000})["total_tax"]
    assert body["total_tax"] == pytest.approx(plain + 11_000, abs=0.01)
    used = _ok(**{**SINGLE, "taxable_profit": 150_000}, stock_relief=100_000,
               stock_relief_regime="young_trained_farmer", state_aid_used=70_000)["stock_relief_cap"]
    assert (used["cap"], used["clawback"]) == (30_000, 21_000)


def test_small_relief_under_the_cap_costs_nothing():
    body = _ok(**{**SINGLE, "business_type": "partnership"}, stock_relief=5_000, stock_relief_regime="registered_partnership")
    assert body["stock_relief_cap"]["clawback"] == 0 and body["stock_relief_cap"]["cap"] == 20_000


def test_2027_rules_are_flagged_as_announced():
    rules = {r["rule_id"]: r for r in _ok(**{**SINGLE, "tax_year": 2027})["rules_applied"]}
    assert (rules["it_band_single"]["value"], rules["it_band_single"]["status"]) == (46_500, "announced")
    assert rules["it_rate_standard"]["status"] == "enacted"


def test_errors():
    assert _reason(**{**SINGLE, "tax_year": 2028}) == "rule_not_available"
    assert _reason(**{**SINGLE, "business_type": "company"}, marital_status="married") == "regime_not_available"
    assert _reason(**SINGLE, spouse_paye_income=10_000) == "spouse_needs_married"
    assert _reason(**SINGLE, stock_relief_regime="registered_partnership") == "regime_not_available"


def test_feeds_debt_capacity():
    """Platform passes total_tax as debt.capacity tax: no maths in between."""
    tax = _ok(**SINGLE)["total_tax"]
    months = [{"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000} for m in range(1, 13)]
    body = run_function("debt.capacity", {"months": months, "tax": tax, "annual_rate": 0.05, "term_months": 120})["result"]
    assert body["repayment_capacity"] == pytest.approx(12 * 8_000 - tax, abs=0.01)


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.estimate/run", json=SINGLE).json() == _run(**SINGLE)


# Income averaging (s.657, ADR-0055), tax year 2026, single.
#   prior 40,000 / 50,000 / 60,000 / 70,000; this year 62,000 after 8,000 allowances
#   → 70,000 before allowances; average (40 + 50 + 60 + 70 + 70)k / 5 = 58,000
#   → assessable 58,000 − 8,000 = 50,000
#   IT 44,000 × 20% + 6,000 × 40% = 11,200 − 4,000 = 7,200
#   USC 60.06 + 333.76 + 21,300 × 3% = 1,032.82; PRSI 50,000 × 4.2375% = 2,118.75
#   total 10,351.57
AVERAGING = {
    **SINGLE, "taxable_profit": 62_000, "income_averaging": True,
    "prior_farming_profits": [40_000, 50_000, 60_000, 70_000], "capital_allowances": 8_000,
}


def test_averaging_assesses_the_five_year_average():
    body = _ok(**AVERAGING)
    assert body["averaging"] == {
        "years": 5,
        "profits_before_allowances": [40_000, 50_000, 60_000, 70_000, 70_000],
        "averaged_profit": 58_000,
        "capital_allowances": 8_000,
        "assessable_profit": 50_000,
    }
    assert body["income"]["farm_profit"] == 50_000
    assert (body["income_tax"]["net"], body["usc"]["total"], body["prsi"]["total"]) == (7_200, 1_032.82, 2_118.75)
    assert body["total_tax"] == 10_351.57
    # Same tax as an actual-basis year on 50,000; the rule used is listed.
    assert body["total_tax"] == _ok(**{**SINGLE, "taxable_profit": 50_000})["total_tax"]
    rule = body["rules_applied"][-1]
    assert (rule["rule_id"], rule["value"], rule["legal_ref"]) == ("income_averaging_years", 5, "TCA s.657")
    assert _ok(**SINGLE)["averaging"] is None


def test_averaging_net_loss_is_nil():
    body = _ok(**{**AVERAGING, "taxable_profit": -20_000, "capital_allowances": 0,
                  "prior_farming_profits": [-30_000, 10_000, 0, 5_000]})
    assert body["averaging"]["averaged_profit"] == -7_000
    assert body["total_tax"] == 0 and body["income"]["total"] == 0


def test_averaging_relief_counts_a_fifth_towards_the_cap():
    """100,000 young trained farmer relief moves the average by 20,000 only."""
    body = _ok(**AVERAGING, stock_relief=100_000, stock_relief_regime="young_trained_farmer")
    assert body["stock_relief_cap"]["relief"] == 20_000


def test_individuals_must_answer_averaging():
    result = _run(**{k: v for k, v in SINGLE.items() if k != "income_averaging"})
    assert result["status"] == "needs_input"
    assert result["missing"] == [{"field": "income_averaging", "unit": "boolean", "path": "income_averaging"}]
    # Companies never average: no answer needed.
    assert _ok(business_type="company", tax_year=2026, taxable_profit=10_000)["averaging"] is None


def test_averaging_asks_for_its_history():
    result = _run(**{**SINGLE, "income_averaging": True})
    assert result["status"] == "needs_input"
    assert [m["path"] for m in result["missing"]] == ["prior_farming_profits", "capital_allowances"]
    assert [m["unit"] for m in result["missing"]] == ["list", "EUR"]


def test_averaging_errors():
    assert _reason(**{**AVERAGING, "prior_farming_profits": [1, 2, 3]}) == "averaging_years_invalid"
    assert _reason(**SINGLE, prior_farming_profits=[1, 2, 3, 4]) == "needs_income_averaging"
    assert _reason(**SINGLE, capital_allowances=0) == "needs_income_averaging"
    assert _reason(business_type="company", tax_year=2026, taxable_profit=1, income_averaging=True) == "regime_not_available"
