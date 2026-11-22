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
    body = run_function("debt.capacity", {"months": months, "tax": tax, "tax_source": "estimate", "annual_rate": 0.05, "term_months": 120})["result"]
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


# Losses carried forward (s.382, ADR-0055 §5a), single 2026.
def test_losses_forward_reduce_the_profit_charged():
    """60,000 − 10,000 losses = 50,000: the same tax as a 50,000 year (10,351.57)."""
    body = _ok(**SINGLE, losses_forward=10_000)
    assert body["losses"] == {
        "brought_forward": 10_000, "used": 10_000, "lost_by_stock_relief": 0, "this_year_loss": 0,
        "carried_forward": 0, "prsi_treatment": "reduced_unconfirmed",
    }
    assert body["income"]["farm_profit"] == 50_000 and body["total_tax"] == 10_351.57


def test_unused_losses_carry_on():
    body = _ok(**SINGLE, losses_forward=80_000)
    assert (body["losses"]["used"], body["losses"]["carried_forward"], body["total_tax"]) == (60_000, 20_000, 0)


def test_stock_relief_claim_stops_losses_going_further():
    """s.666(3): in a stock relief claim year the 20,000 left over cannot be carried on."""
    losses = _ok(**SINGLE, losses_forward=80_000, stock_relief=3_000)["losses"]
    assert (losses["used"], losses["lost_by_stock_relief"], losses["carried_forward"]) == (60_000, 20_000, 0)


def test_a_loss_year_adds_to_what_is_carried():
    losses = _ok(**{**SINGLE, "taxable_profit": -15_000}, losses_forward=5_000)["losses"]
    assert (losses["used"], losses["this_year_loss"], losses["carried_forward"]) == (0, 15_000, 20_000)


def test_losses_come_after_averaging():
    """Averaged assessable 50,000 (see AVERAGING) − 5,000 losses = 45,000."""
    body = _ok(**AVERAGING, losses_forward=5_000)
    assert body["averaging"]["assessable_profit"] == 50_000 and body["income"]["farm_profit"] == 45_000


def test_company_losses_are_not_modelled():
    result = _run(business_type="company", tax_year=2026, taxable_profit=10_000, losses_forward=1_000)
    assert result["errors"][0]["details"]["reason"] == "regime_not_available"
    assert _ok(business_type="company", tax_year=2026, taxable_profit=10_000)["losses"] is None


# Pension contributions (s.787, ADR-0055 §5b), single 2026, 60,000 profit, born 1981 → 45 → 25%.
#   limit 25% × 60,000 = 15,000; 10,000 paid → all relieved, income tax only:
#   IT on 50,000 = 8,800 + 2,400 − 4,000 = 7,200 (was 11,200); USC 1,332.82, PRSI 2,542.50 unchanged
#   total 11,075.32
def test_pension_relief_is_income_tax_only():
    body = _ok(**SINGLE, pension_contributions=10_000, birth_year=1981)
    assert body["pension"] == {
        "contributions": 10_000, "age": 45, "age_pct": 25, "net_relevant_earnings": 60_000,
        "earnings_basis": "assessable_farm_profit", "limit": 15_000, "relief": 10_000, "unrelieved": 0,
    }
    assert body["income_tax"]["net"] == 7_200
    assert (body["usc"]["total"], body["prsi"]["total"]) == (1_332.82, 2_542.5)
    assert body["total_tax"] == 11_075.32
    assert {"pension_pct_from_age_40", "pension_earnings_cap"} <= {r["rule_id"] for r in body["rules_applied"]}


def test_pension_above_the_limit_is_carried():
    """20,000 paid, 15,000 relieved: IT on 45,000 = 8,800 + 400 − 4,000 = 5,200."""
    body = _ok(**SINGLE, pension_contributions=20_000, birth_year=1981)
    assert (body["pension"]["relief"], body["pension"]["unrelieved"], body["income_tax"]["net"]) == (15_000, 5_000, 5_200)


def test_pension_age_bands_and_earnings_cap():
    assert _ok(**SINGLE, pension_contributions=1, birth_year=1996)["pension"]["age_pct"] == 20  # 30 in 2026
    assert _ok(**SINGLE, pension_contributions=1, birth_year=1997)["pension"]["age_pct"] == 15  # 29
    high = _ok(**{**SINGLE, "taxable_profit": 200_000}, pension_contributions=60_000, birth_year=1964)["pension"]
    assert (high["age_pct"], high["limit"], high["relief"]) == (40, 46_000, 46_000)  # 40% × 115,000


def test_pension_uses_profit_after_averaging_and_losses():
    """Averaged 50,000 − 5,000 losses = 45,000 earnings → 25% limit 11,250."""
    pension = _ok(**AVERAGING, losses_forward=5_000, pension_contributions=20_000, birth_year=1981)["pension"]
    assert (pension["net_relevant_earnings"], pension["limit"]) == (45_000, 11_250)


def test_pension_inputs():
    missing = _run(**SINGLE, pension_contributions=5_000)
    assert missing["status"] == "needs_input" and [m["path"] for m in missing["missing"]] == ["birth_year"]
    assert _reason(**SINGLE, birth_year=1981) == "birth_year_invalid"
    assert _reason(business_type="company", tax_year=2026, taxable_profit=1, pension_contributions=1, birth_year=1980) == "regime_not_available"
    assert _ok(**SINGLE)["pension"] is None


# Home carer credit (s.466A, ADR-0055 §5c), married 2026, farm profit 60,000.
#   Spouse no income: credit 1,950 (no band increase to lose):
#     IT 53,000 × 20% + 7,000 × 40% = 13,400 − (4,000 + 2,000 + 1,950) = 5,450 (7,400 without)
#   Spouse PAYE 9,000: credit 1,950 − (9,000 − 7,200) / 2 = 1,050
#     band increase: 62,000 band → 15,200 − (4,000 + 2,000 + 1,800) = 7,400
#     credit:        53,000 band → 17,000 − (7,800 + 1,050) = 8,150 → band increase is better
MARRIED = {**SINGLE, "marital_status": "married"}


def test_home_carer_credit_with_no_second_income():
    body = _ok(**MARRIED, home_carer=True)
    assert body["home_carer"] == {"credit_after_taper": 1_950, "applied": "credit"}
    assert body["income_tax"]["net"] == 5_450
    assert _ok(**MARRIED)["income_tax"]["net"] == 7_400 and _ok(**MARRIED)["home_carer"] is None


def test_home_carer_or_band_increase_whichever_is_better():
    body = _ok(**MARRIED, spouse_paye_income=9_000, home_carer=True)
    assert body["home_carer"] == {"credit_after_taper": 1_050, "applied": "band_increase"}
    assert body["income_tax"]["net"] == 7_400 and body["income_tax"]["standard_rate_band"] == 62_000


def test_home_carer_credit_tapers_to_nil():
    body = _ok(**MARRIED, spouse_paye_income=12_000, home_carer=True)
    assert body["home_carer"] == {"credit_after_taper": 0, "applied": "band_increase"}


def test_home_carer_rules_and_eligibility():
    rules = {r["rule_id"]: r["value"] for r in _ok(**MARRIED, home_carer=True)["rules_applied"]}
    assert (rules["home_carer_credit"], rules["home_carer_income_limit"]) == (1_950, 7_200)
    assert _ok(**{**MARRIED, "tax_year": 2024}, home_carer=True)["home_carer"]["credit_after_taper"] == 1_800
    assert _reason(**{**MARRIED, "tax_year": 2027}, home_carer=True) == "rule_not_available"
    assert _reason(**SINGLE, home_carer=True) == "spouse_needs_married"


# Spouse's own income (ADR-0055 §5d), married 2026, farm profit 60,000.
#   Own trade 30,000: same band (83,000) and credits (earned income instead of employee),
#   USC 432.82, Class S 30,000 × 4.2375% = 1,271.25 → 16,979.39, as PAYE pay of 30,000
#   Farm wages 30,000: same income tax and USC, no PRSI (excepted employment) → 15,708.14
#   PAYE 8,000 + own trade 8,000: credits 1,600 + 1,600 capped at 2,000 per person;
#     band 53,000 + 16,000 = 69,000; IT 13,800 + 2,800 − 8,000 = 8,600;
#     PRSI: Class A nil (153.85 a week), Class S minimum 650
def test_spouse_own_trade():
    body = _ok(**MARRIED, spouse_self_employed_income=30_000)
    assert body["income"]["spouse_self_employed_income"] == 30_000 and body["income"]["total"] == 90_000
    assert body["income_tax"]["standard_rate_band"] == 83_000 and body["income_tax"]["net"] == 11_400
    assert (body["usc"]["spouse"], body["prsi"]["spouse"], body["total_tax"]) == (432.82, 1_271.25, 16_979.39)


def test_spouse_paid_by_the_farm_pays_no_prsi():
    body = _ok(**MARRIED, spouse_farm_wages=30_000)
    assert body["income_tax"]["net"] == 11_400 and body["usc"]["spouse"] == 432.82
    assert body["prsi"]["spouse"] == 0 and body["total_tax"] == 15_708.14


def test_spouse_credits_share_one_cap():
    body = _ok(**MARRIED, spouse_paye_income=8_000, spouse_self_employed_income=8_000)
    assert body["income_tax"]["standard_rate_band"] == 69_000
    assert (body["income_tax"]["credits"], body["income_tax"]["net"]) == (8_000, 8_600)
    assert body["prsi"]["spouse"] == 650


def test_home_carer_counts_all_the_spouse_income():
    assert _ok(**MARRIED, spouse_self_employed_income=9_000, home_carer=True)["home_carer"]["credit_after_taper"] == 1_050


def test_spouse_income_errors():
    assert _reason(**SINGLE, spouse_self_employed_income=1) == "spouse_needs_married"
    assert _reason(**{**MARRIED, "business_type": "partnership"}, spouse_farm_wages=1) == "regime_not_available"


# Step-out year (s.657(6A), ADR-0055 §8a), single 2026, a poor year after four good ones:
#   prior 60,000 × 4; this year 20,000 after 8,000 allowances (28,000 before)
#   averaged (240,000 + 28,000) / 5 = 53,600 − 8,000 = 45,600 → IT 8,800 + 640 − 4,000 = 5,440
#   actual 20,000 → IT 4,000 − 4,000 = 0; USC 60.06 + 7,988 × 2% = 219.82; PRSI 847.50 → 1,067.32
#   deferred income tax 5,440 → 4 × 1,360 on 31 Oct 2028, 2029, 2030, 2031
STEP_OUT = {**SINGLE, "taxable_profit": 20_000, "income_averaging": True,
            "prior_farming_profits": [60_000] * 4, "capital_allowances": 8_000,
            "step_out": True, "last_step_out_year": "never"}


def test_step_out_taxes_actual_and_defers_the_rest():
    body = _ok(**STEP_OUT)
    assert body["income"]["farm_profit"] == 20_000 and body["total_tax"] == 1_067.32
    assert body["averaging"]["assessable_profit"] == 45_600
    step = body["step_out"]
    assert (step["income_tax_on_average"], step["income_tax_on_actual"], step["deferred_income_tax"]) == (5_440, 0, 5_440)
    assert step["instalments"] == [{"due": f"{y}-10-31", "amount": 1_360} for y in (2028, 2029, 2030, 2031)]
    ids = {r["rule_id"] for r in body["rules_applied"]}
    assert {"income_averaging_years", "averaging_step_out_instalments", "averaging_step_out_gap_years"} <= ids
    assert _ok(**SINGLE)["step_out"] is None


def test_step_out_never_defers_a_negative():
    """A better year than the average: nothing to defer."""
    body = _ok(**{**STEP_OUT, "taxable_profit": 90_000})
    assert body["step_out"]["deferred_income_tax"] == 0 and body["step_out"]["instalments"][0]["amount"] == 0


def test_step_out_rules():
    missing = _run(**{k: v for k, v in STEP_OUT.items() if k != "last_step_out_year"})
    assert [m["path"] for m in missing["missing"]] == ["last_step_out_year"]
    assert _reason(**{**STEP_OUT, "last_step_out_year": 2022}) == "step_out_too_soon"  # within 4 years
    assert _ok(**{**STEP_OUT, "last_step_out_year": 2021})["step_out"]["last_step_out_year"] == 2021
    assert _reason(**SINGLE, step_out=True, last_step_out_year="never") == "needs_income_averaging"
    assert _reason(**SINGLE, last_step_out_year=2020) == "needs_income_averaging"


# Review fix: the stock relief cap measures the relief against a no-relief year with
# the same losses and pension limit applied to the higher profit.
def test_cap_counts_losses_in_the_no_relief_case():
    """20,000 after 150,000 young farmer relief, 200,000 losses: without the relief the
    170,000 would still be covered by losses, so the relief saves nothing — no clawback
    (it was 16,730.62 of tax on nil income)."""
    body = _ok(**{**SINGLE, "taxable_profit": 20_000}, stock_relief=150_000,
               stock_relief_regime="young_trained_farmer", losses_forward=200_000)
    assert (body["stock_relief_cap"]["tax_value"], body["stock_relief_cap"]["clawback"]) == (0, 0)
    assert body["total_tax"] == 0


def test_cap_recomputes_the_pension_limit():
    """60,000 after 30,000 relief, 20,000 pension, age 45 (25%):
    with relief:    limit 15,000 → IT on 45,000 = 5,200; USC on 60,000 = 1,332.82
    without relief: limit 22,500 → all 20,000 → IT on 70,000 = 15,200; USC on 90,000 = 3,230.62
    tax value 10,000 + 1,897.80 = 11,897.80 (was 13,897.80 with the 15,000 limit reused)."""
    cap = _ok(**SINGLE, stock_relief=30_000, stock_relief_regime="young_trained_farmer",
              pension_contributions=20_000, birth_year=1981)["stock_relief_cap"]
    assert cap["tax_value"] == 11_897.8
