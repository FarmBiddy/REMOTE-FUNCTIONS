"""Per-ID discovery (ADR-0048): input schema + units for every public ID."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.registry import PUBLIC_CALCULATION_IDS, REQUIRED_FIELDS, describe_function
from farm_functions.runner import run_function

client = TestClient(app)


@pytest.mark.parametrize("key", PUBLIC_CALCULATION_IDS)
def test_every_id_is_described_with_units(key):
    detail = describe_function(key)
    assert detail["key"] == key
    assert detail["required"] == list(REQUIRED_FIELDS[key])
    assert detail["input_schema"]["type"] == "object"
    unknown = [name for name, unit in detail["units"].items() if unit == "unknown"]
    assert unknown == [], f"{key}: fields without a unit {unknown}"


def test_nested_fields_are_described():
    detail = describe_function("report.bank")
    assert detail["units"]["pl_months"] == "list"
    assert detail["units"]["milk_litres"] == "litres"
    assert detail["units"]["household_drawings"] == "EUR"
    assert "LoanItemInput" in detail["input_schema"]["$defs"]


def test_choices_are_listed_in_the_schema():
    schema = describe_function("risk.tornado")["input_schema"]
    assert schema["properties"]["rank_by"]["enum"] == ["surplus", "closing_cash", "lowest_cash"]


def test_needs_input_units_match_discovery():
    missing = run_function("plan.projection", {})["missing"]
    units = describe_function("plan.projection")["units"]
    assert all(item["unit"] == units[item["field"]] for item in missing)


def test_http_detail_and_unknown_id():
    body = client.get("/v1/functions/debt.capacity").json()
    assert body == describe_function("debt.capacity")
    missing = client.get("/v1/functions/not.a.function")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "unknown_calculation"
