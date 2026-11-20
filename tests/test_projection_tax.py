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

# When tax is paid (ADR-0055): a steady farm that paid 2025's tax in full on 100% of 2024.
TIMING = {"preliminary_basis": "prior_100",
          "tax_history": [{"tax_year": 2025, "liability": 15_075.32, "preliminary_paid": 15_075.32}]}
BASE = {
    "base_pl_months": [
        {"year": 2025, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 11_000} for m in range(1, 13)
    ],
    "opening_cash": 0,
    "milking_cows": 100,
    "years": 3,
    "tax_profile": {"business_type": "sole_trader", "vat_registered": True, "income_averaging": False, **TIMING},
}
TRACTOR = {"category": "machinery", "cost": 40_000, "year": 2024, "month": 4, "life_months": 120}


def _run(**overrides):
    return run_function("plan.projection", {**BASE, **overrides})


def _years(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]["years"]


def _profile(**fields):
    return {"tax_profile": {"business_type": "sole_trader", "vat_registered": True, "income_averaging": False, **TIMING, **fields}}


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
    years = _years(tax_profile={"business_type": "company", "vat_registered": True})
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


def test_flat_rate_farmers_get_the_vat_addition_in_profit_and_cash():
    """Not VAT-registered: 192,000 milk × 4.5% (2026) = 8,640, then × 4.8% (2027) = 9,216."""
    years = _years(tax_profile={"business_type": "sole_trader", "income_averaging": False, **TIMING})
    assert [y["tax"]["flat_rate_addition"] for y in years[:2]] == [8_640, 9_216]
    assert years[0]["tax"]["profit_before_allowances"] == 68_640
    assert years[0]["cash"]["flat_rate_addition"] == 8_640
    # Cash pays last year's tax on the 100% basis (ADR-0055); this year's liability is owed.
    assert years[0]["cash"]["closing"] == pytest.approx(68_640 - 15_075.32, abs=0.01)
    assert years[0]["balance_sheet"]["tax_owed"] == pytest.approx(years[0]["tax"]["total_tax"] - 15_075.32, abs=0.01)
    assert _years()[0]["cash"]["flat_rate_addition"] == 0  # registered


def test_partnership_is_taxed_per_partner():
    """60,000 split 60 / 40, single partners, 2026:
    36,000 → IT 3,200 + USC 612.82 + PRSI 1,525.50 = 5,338.32
    24,000 → IT 800 + USC 299.82 + PRSI 1,017 = 2,116.82  → 7,455.14, not 15,075.32."""
    profile = {"business_type": "partnership", "vat_registered": True, "income_averaging": False, **TIMING,
               "partners": [{"label": "Joe", "profit_share_pct": 60}, {"label": "Mark", "profit_share_pct": 40}]}
    tax = _years(tax_profile=profile)[0]["tax"]
    assert [p["total_tax"] for p in tax["partners"]] == [5_338.32, 2_116.82]
    assert (tax["total_tax"], tax["stock_relief_regime"]) == (7_455.14, "per_partner")


def test_stock_relief_cap_counts_a_fifth_of_the_relief_when_averaged():
    """Young trained farmer, herd +10% on 1,000,000 → 100,000 relief; profit 66,000 after relief,
    averaged with four zero years = 13,200. With 95,000 of lifetime aid used only 5,000 is left,
    but the relief moves this year's average by 20,000 → about 3,085 of IT + USC: no clawback.
    Tax on 13,200: USC 83.82 + PRSI minimum 650 = 733.82."""
    tax = _years(livestock=1_000_000, assumptions={"herd_pct": [10]}, **_profile(
        young_trained_farmer_first_year=2026, state_aid_used=95_000,
        income_averaging=True, prior_farming_profits=[0, 0, 0, 0]))[0]["tax"]
    assert (tax["stock_relief"], tax["averaged_profit"]) == (100_000, 13_200)
    assert tax["total_tax"] == 733.82


def test_young_farmer_aid_adds_up_across_years():
    """Each year the relief is worth 102,000 of IT + USC; 40,000 a year is allowed until
    the 100,000 lifetime cap leaves only 20,000 in the third year."""
    from farm_functions.tax import projected_tax

    profile = {"business_type": "sole_trader", "vat_registered": True, "registered_partnership": False,
               "young_trained_farmer_first_year": 2025, "income_averaging": False, "prior_farming_profits": [],
               "state_aid_used": 0.0, "other_income": 0.0, "marital_status": "single",
               "spouse_paye_income": 0.0, "partners": []}
    state: dict = {}
    for year in (2025, 2026, 2027):
        projected_tax(profile, state, tax_year=year, period_end_month=12, operating_profit=200_000,
                      livestock_increase=200_000, agricultural_sales=0, register=[])
    assert state["given"][0] == [40_000, 40_000, 20_000]
    assert state["aid"][0] == 100_000


def test_projection_rejects_assets_without_an_allowance_rule():
    old_plant = {"category": "machinery", "cost": 10_000, "year": 2001, "month": 5, "life_months": 120}
    result = _run(assets=[old_plant])
    assert result["errors"][0]["details"]["reason"] == "rule_not_available"
    assert result["errors"][0]["field"] == "assets"


def test_partnership_profile_errors_name_the_field():
    single_partner = {"business_type": "partnership", "income_averaging": False, **TIMING, "partners": [{"profit_share_pct": 100}]}
    result = _run(tax_profile=single_partner)
    assert (result["errors"][0]["details"]["reason"], result["errors"][0]["field"]) == ("partners_invalid", "tax_profile.partners")
    old = [{**m, "year": 2020} for m in BASE["base_pl_months"]]
    assert _run(base_pl_months=old)["errors"][0]["field"] == "base_pl_months"


def test_rules_status_counts_every_rule_the_year_used(monkeypatch):
    """A year whose tax rules are law but whose flat-rate addition is only announced
    is labelled 'announced' (today no such year exists, so the VAT table is patched)."""
    from datetime import date

    import farm_functions.tax as tax
    from farm_functions.ie.rules import Rule

    assert _years(tax_profile={"business_type": "sole_trader", "income_averaging": False, **TIMING})[0]["tax"]["rules_status"] == "enacted"  # 2026
    announced = (Rule("vat_fra", 4.5, date(2026, 1, 1), None, "test", "announced"),)
    monkeypatch.setattr(tax, "FLAT_RATE_ADDITION", announced)
    assert _years(tax_profile={"business_type": "sole_trader", "income_averaging": False, **TIMING})[0]["tax"]["rules_status"] == "announced"


def test_individuals_must_answer_averaging():
    """ADR-0055: no default; companies leave it unset."""
    result = _run(tax_profile={"business_type": "sole_trader", "vat_registered": True})
    assert result["status"] == "needs_input"
    assert [m["path"] for m in result["missing"]] == [
        "tax_profile.income_averaging", "tax_profile.preliminary_basis", "tax_profile.tax_history",
    ]
    assert _years(tax_profile={"business_type": "company", "vat_registered": True})[0]["tax"]["averaging"] == "off"


# When tax is paid (ADR-0055 §2c), calendar year end: each October pays that year's
# preliminary + last year's balance. Liabilities 2026 15,075.32, 2027 14,399.32.
#   90% basis, 2025 owed 20,000 with 16,000 preliminary paid:
#   2026: 90% × 15,075.32 = 13,567.79 + 4,000 = 17,567.79; owed 15,075.32 − 13,567.79 = 1,507.53
#   2027: 90% × 14,399.32 = 12,959.39 + 1,507.53 = 14,466.92; owed 1,439.93
def test_irish_timing_on_the_90_percent_basis():
    years = _years(**_profile(preliminary_basis="current_90",
                              tax_history=[{"tax_year": 2025, "liability": 20_000, "preliminary_paid": 16_000}]))
    first, second = years[0], years[1]
    assert first["tax"]["payments"] == {
        "pay_year": 2026, "preliminary_basis": "current_90", "preliminary": 13_567.79,
        "balance_previous_year": 4_000, "refund_previous_year": 0, "paid": 17_567.79, "owed_at_year_end": 1_507.53,
    }
    assert (first["cash"]["tax"], first["cash"]["tax_refund"], first["cash"]["closing"]) == (17_567.79, 0, 42_432.21)
    assert first["balance_sheet"]["tax_owed"] == 1_507.53
    assert first["balance_sheet"]["net_worth"] == pytest.approx(42_432.21 - 1_507.53, abs=0.01)
    assert (second["cash"]["tax"], second["balance_sheet"]["tax_owed"]) == (14_466.92, 1_439.93)
    # The year's own tax is unchanged, and cover stays on it.
    assert first["tax"]["total_tax"] == 15_075.32


def test_overpaid_last_year_comes_back_gross():
    """100% basis after a better 2025 (30,000 owed, 40,000 paid): 2026 pays 30,000
    preliminary and gets 10,000 back; 2026 then ends overpaid by 14,924.68."""
    first = _years(**_profile(tax_history=[{"tax_year": 2025, "liability": 30_000, "preliminary_paid": 40_000}]))[0]
    assert (first["cash"]["tax"], first["cash"]["tax_refund"]) == (30_000, 10_000)
    assert first["cash"]["closing"] == 40_000
    assert first["balance_sheet"]["tax_owed"] == -14_924.68


def test_timing_errors():
    def reason(**fields):
        result = _run(**_profile(**fields))
        assert result["status"] == "error", result
        return result["errors"][0]["details"]["reason"]

    assert reason(tax_history=[{"tax_year": 2024, "liability": 1, "preliminary_paid": 1}]) == "tax_history_invalid"
    assert reason(tax_history=[{"tax_year": 2025, "liability": 1}]) == "tax_history_invalid"
    assert reason(tax_history=[{"tax_year": 2025, "liability": 1, "preliminary_paid": 1},
                               {"tax_year": 2025, "liability": 1, "preliminary_paid": 1}]) == "tax_history_invalid"
    company = _run(tax_profile={"business_type": "company", "vat_registered": True, "preliminary_basis": "prior_100"})
    assert company["errors"][0]["details"]["reason"] == "regime_not_available"
    assert _run(**_profile(preliminary_basis="pre_preceding_105_dd"))["status"] == "error"


def test_company_and_caller_tax_are_paid_in_the_year():
    company = _years(tax_profile={"business_type": "company", "vat_registered": True})[0]
    assert company["tax"]["payments"] is None and company["cash"]["tax"] == 7_500
    assert company["balance_sheet"]["tax_owed"] == 0
