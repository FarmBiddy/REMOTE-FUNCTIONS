"""plan.projection with tax_profile (ADR-0053 phase 5): tax per projected year.

Base 2025: 12 × (16,000 milk − 11,000 feed) = 60,000 surplus a year, no loans.
  2026 single, 60,000: IT 11,200 + USC 1,332.82 + PRSI 2,542.50 = 15,075.32
  2027 (announced): IT 46,500 × 20% + 13,500 × 40% − 4,250 = 10,450;
       USC 60.06 + 18,288 × 2% + 29,700 × 3% = 1,316.82; PRSI 60,000 × 4.3875% = 2,632.50
       → 14,399.32; 2028 has no rules: 2027 held constant → same
Averaging, prior years 0, 0, 0, 0:
  2026 average 12,000 → IT nil after credits, USC exempt, PRSI minimum 650
  2027 window 0, 0, 0, 60,000, 60,000 → 24,000: IT 4,800 − 4,250 = 550,
       USC 60.06 + 11,988 × 2% = 299.82, PRSI 24,000 × 4.3875% = 1,053 → 1,902.82
"""

import pytest

from farm_functions.runner import run_function

BASE = {
    "base_pl_months": [
        {"year": 2025, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 11_000} for m in range(1, 13)
    ],
    "opening_cash": 0,
    "milking_cows": 100,
    "years": 3,
    "tax_profile": {"business_type": "sole_trader"},
}
TRACTOR = {"category": "machinery", "cost": 40_000, "year": 2024, "month": 4, "life_months": 120}


def _run(**overrides):
    return run_function("plan.projection", {**BASE, **overrides})


def _years(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]["years"]


def _profile(**fields):
    return {"tax_profile": {"business_type": "sole_trader", **fields}}


def test_tax_per_year_with_rules_in_force_then_held_constant():
    years = _years()
    assert [y["tax"]["total_tax"] for y in years] == [15_075.32, 14_399.32, 14_399.32]
    assert [y["tax"]["tax_year"] for y in years] == [2026, 2027, 2028]
    assert [y["tax"]["rules_basis"] for y in years] == ["in_force", "in_force", "latest_held_constant"]
    assert years[1]["tax"]["rules_status"] == "announced"
    assert years[0]["cash"]["tax"] == 15_075.32 and years[0]["assumptions_used"]["tax"] == 15_075.32
    assert years[0]["cash"]["closing"] == pytest.approx(60_000 - 15_075.32, abs=0.01)


def test_income_averaging_uses_prior_years_then_projected_ones():
    years = _years(**_profile(income_averaging=True, prior_farming_profits=[0, 0, 0, 0]))
    assert [(y["tax"]["averaging"], y["tax"]["averaged_profit"]) for y in years[:2]] == [
        ("applied", 12_000), ("applied", 24_000)
    ]
    assert [y["tax"]["total_tax"] for y in years[:2]] == [650, 1_902.82]


def test_averaging_without_history_waits_for_a_full_window():
    years = _years(**_profile(income_averaging=True))
    assert {y["tax"]["averaging"] for y in years} == {"insufficient_history"}
    assert years[0]["tax"]["total_tax"] == 15_075.32  # taxed on actual profit


def test_capital_allowances_come_after_averaging():
    """s.657: average profit before allowances, then deduct this year's 5,000."""
    plain = _years(assets=[TRACTOR])[0]["tax"]
    assert (plain["capital_allowances"], plain["assessable_profit"]) == (5_000, 55_000)
    averaged = _years(assets=[TRACTOR], **_profile(income_averaging=True, prior_farming_profits=[0, 0, 0, 0]))[0]["tax"]
    assert (averaged["averaged_profit"], averaged["assessable_profit"]) == (12_000, 7_000)


def test_herd_growth_is_taxable_and_gets_stock_relief():
    """Herd +10%: 300,000 → 330,000 livestock value, 25% relief = 7,500.
    Surplus grows too: litres and feed × 1.1 → 66,000."""
    tax = _years(livestock=300_000, assumptions={"herd_pct": [10]})[0]["tax"]
    assert (tax["livestock_increase"], tax["profit_before_allowances"]) == (30_000, 96_000)
    assert (tax["stock_relief_regime"], tax["stock_relief"], tax["assessable_profit"]) == ("general", 7_500, 88_500)


def test_company_projection_pays_corporation_tax():
    years = _years(tax_profile={"business_type": "company"})
    assert years[0]["tax"]["total_tax"] == 7_500  # 60,000 × 12.5%


def test_no_profile_keeps_caller_tax():
    years = _years(tax_profile=None, assumptions={"tax": [9_000]})
    assert years[0]["tax"] is None and years[0]["cash"]["tax"] == 9_000


def test_errors():
    def reason(**overrides):
        result = _run(**overrides)
        assert result["status"] == "error"
        return result["errors"][0]["details"]["reason"]

    assert reason(assumptions={"tax": [9_000]}) == "tax_conflict"
    assert reason(tax_profile={"business_type": "company", "income_averaging": True}) == "regime_not_available"
    old = [{**m, "year": 2020} for m in BASE["base_pl_months"]]
    assert reason(base_pl_months=old) == "rule_not_available"
