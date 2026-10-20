"""tax.capital_allowances (ADR-0053): Irish capital allowances for one tax year.

Hand check, tax year 2026 (calendar accounts):
  tractor 2024, 40,000            12.5% × 8: year 3 → opening 30,000, allowance 5,000
  shed 2021, 70,000 − 10,000 grant 15% × 6 + 10%: year 6 → opening 15,000 (75% given), 9,000
  slurry tank 2025, 50,000 − 20,000 grant 50% × 2: year 2 → opening 15,000, 15,000
  safety rail 2026, 2,000          50% × 2: year 1 → 1,000
  total 30,000; accounting profit 40,000 + depreciation 12,000 − 30,000 = taxable 22,000
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.ie.capital_allowances import SCHEDULES
from farm_functions.runner import run_function

client = TestClient(app)

TRACTOR = {"category": "machinery", "cost": 40_000, "year": 2024, "month": 4, "life_months": 120}
SHED = {"category": "buildings", "cost": 70_000, "grant": 10_000, "year": 2021, "month": 9, "life_months": 300}
SLURRY = {**SHED, "cost": 50_000, "grant": 20_000, "year": 2025, "month": 3, "tax_allowance": "slurry_storage"}
RAIL = {"category": "other", "cost": 2_000, "year": 2026, "month": 1, "life_months": 60, "tax_allowance": "farm_safety"}
BASE = {"tax_year": 2026, "assets": [TRACTOR, SHED, SLURRY, RAIL], "accounting_profit": 40_000, "depreciation": 12_000}


def _run(**overrides):
    return run_function("tax.capital_allowances", {**BASE, **overrides})


def _ok(**overrides):
    result = _run(**overrides)
    assert result["status"] == "ok", result
    return result["result"]


def test_reference_year():
    body = _ok()
    assert [(a["opening_twdv"], a["allowance"], a["closing_twdv"]) for a in body["assets"]] == [
        (30_000, 5_000, 25_000), (15_000, 9_000, 6_000), (15_000, 15_000, 0), (2_000, 1_000, 1_000)
    ]
    assert body["by_type"] == {"plant": 5_000, "farm_buildings": 9_000, "slurry_storage": 15_000, "farm_safety": 1_000}
    assert body["total"]["allowance"] == 30_000
    assert body["profit_bridge"] == {
        "accounting_profit": 40_000, "add_back_depreciation": 12_000, "flat_rate_addition": 0,
        "capital_allowances": 30_000, "taxable_profit": 22_000,
    }
    assert body["caps_not_applied"] == ["ca_accelerated_cap"]


def test_schedules_write_off_exactly_the_qualifying_cost():
    for schedule in SCHEDULES.values():
        assert sum(schedule) == 100


def test_written_off_and_future_assets_give_nothing():
    body = _ok(tax_year=2033, assets=[TRACTOR, {**TRACTOR, "year": 2034}])  # tractor's 10th year
    assert [a["allowance"] for a in body["assets"]] == [0, 0]
    assert body["assets"][0]["opening_twdv"] == 0


def test_period_end_month_sets_the_tax_year_of_the_spend():
    """Bought Nov 2025 with accounts to September: in the year ending Sep 2026."""
    asset = {**TRACTOR, "year": 2025, "month": 11}
    assert _ok(period_end_month=9, assets=[asset])["assets"][0]["opening_twdv"] == 40_000
    assert _ok(period_end_month=12, assets=[asset])["assets"][0]["opening_twdv"] == 35_000


def test_accelerated_scheme_outside_its_window_falls_back():
    old_tank = {**SLURRY, "year": 2020}  # before 2023: normal farm buildings
    body = _ok(assets=[old_tank])
    assert body["assets"][0]["allowance_applied"] == "farm_buildings"
    assert body["assets"][0]["allowance"] == 3_000  # 2020 → 2026 is year 7: 30,000 × 10%
    rail_2027 = _ok(tax_year=2027, assets=[{**RAIL, "year": 2027}])
    assert rail_2027["rules_applied"][0]["status"] == "announced"


def test_other_assets_get_no_allowance_unless_typed():
    body = _ok(assets=[{**RAIL, "tax_allowance": None}])
    assert (body["assets"][0]["allowance_applied"], body["assets"][0]["allowance"]) == ("none", 0)


def test_no_bridge_without_accounting_profit():
    assert _ok(accounting_profit=None)["profit_bridge"] is None


def test_errors():
    result = _run(assets=[{**TRACTOR, "grant": 50_000}])
    assert result["errors"][0]["details"]["reason"] == "grant_above_cost"
    result = _run(assets=[{**TRACTOR, "year": 2001}])
    assert result["errors"][0]["details"]["reason"] == "rule_not_available"


def test_register_still_works_for_assets_schedule():
    """grant / tax_allowance are tax-only: accounting depreciation ignores them."""
    period = {"from_year": 2026, "from_month": 1, "to_year": 2026, "to_month": 12}
    assert run_function("assets.schedule", {"assets": BASE["assets"], **period})["status"] == "ok"


def test_http_matches_runner():
    assert client.post("/v1/functions/tax.capital_allowances/run", json=BASE).json() == _run()


def test_flat_rate_addition_is_taxable_income():
    assert _ok(flat_rate_addition=5_000)["profit_bridge"]["taxable_profit"] == 27_000


def test_slurry_equipment_falls_back_to_plant_not_buildings():
    """An agitator (machinery) typed slurry_storage, bought 2022: plant at 12.5%."""
    agitator = {"category": "machinery", "cost": 8_000, "year": 2022, "month": 6, "life_months": 120,
                "tax_allowance": "slurry_storage"}
    asset = _ok(assets=[agitator])["assets"][0]
    assert (asset["allowance_applied"], asset["allowance"]) == ("plant", 1_000)
