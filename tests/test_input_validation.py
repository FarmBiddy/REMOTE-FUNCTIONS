import pytest
from pydantic import ValidationError

from farm_functions.domain import FinancialInput
from farm_functions.runner import run_function
from farm_functions.schemas import FIELD_UNITS, list_input_metadata

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}


def test_explicit_zero_is_valid():
    result = run_function(
        "pl.summary",
        {
            "milking_cows": 0,
            "litres_per_cow": 0,
            "milk_price": 0,
            "biss": 0,
            "feed": 0,
        },
    )
    assert result["status"] == "ok"
    assert result["result"]["revenue"]["total"] == 0
    assert result["result"]["costs"]["total"] == 0
    parsed = FinancialInput.model_validate(
        {"milking_cows": 0, "litres_per_cow": 0, "milk_price": 0}
    )
    assert parsed.milking_cows == 0
    assert parsed.feed == 0


def test_missing_required_returns_needs_input():
    result = run_function("pl.summary", {"milking_cows": 100, "litres_per_cow": 5000})
    assert result["status"] == "needs_input"
    assert result["missing"] == [{"field": "milk_price", "unit": "EUR/litre"}]


def test_omitted_optional_defaults_to_zero():
    result = run_function("pl.summary", SAMPLE_MILK)
    assert result["status"] == "ok"
    assert result["result"]["revenue"]["schemes"] == 0
    assert result["result"]["costs"]["total"] == 0
    parsed = FinancialInput.model_validate(SAMPLE_MILK)
    assert parsed.biss == 0
    assert parsed.feed == 0


def test_null_required_field_is_invalid():
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": None},
    )
    assert result["status"] == "error"
    assert result["details"] == [
        {"field": "milk_price", "reason": "null is not a valid value"}
    ]


def test_null_optional_field_is_invalid():
    result = run_function("pl.summary", {**SAMPLE_MILK, "feed": None})
    assert result["status"] == "error"
    assert result["details"] == [{"field": "feed", "reason": "null is not a valid value"}]


def test_negative_cows_rejected():
    result = run_function("revenue.milk", {**SAMPLE_MILK, "milking_cows": -1})
    assert result["status"] == "error"
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({**SAMPLE_MILK, "milking_cows": -1})


def test_negative_litres_rejected():
    result = run_function("revenue.milk", {**SAMPLE_MILK, "litres_per_cow": -1})
    assert result["status"] == "error"


def test_negative_milk_price_rejected():
    result = run_function("revenue.milk", {**SAMPLE_MILK, "milk_price": -0.01})
    assert result["status"] == "error"


def test_negative_revenue_and_cost_lines_rejected():
    assert run_function("pl.summary", {**SAMPLE_MILK, "biss": -1})["status"] == "error"
    assert run_function("pl.summary", {**SAMPLE_MILK, "cattle_sales": -1})["status"] == "error"
    assert run_function("pl.summary", {**SAMPLE_MILK, "feed": -1})["status"] == "error"
    assert run_function("pl.summary", {**SAMPLE_MILK, "loan_repayments": -5})["status"] == "error"
    assert run_function("profit.net", {"revenue": -1, "costs": 0})["status"] == "error"
    assert run_function("profit.net", {"revenue": 0, "costs": -1})["status"] == "error"


def test_wrong_types_rejected():
    assert run_function("revenue.milk", {**SAMPLE_MILK, "milk_price": "0.40"})["status"] == "error"
    assert run_function("revenue.milk", {**SAMPLE_MILK, "milking_cows": True})["status"] == "error"
    assert run_function("pl.summary", {**SAMPLE_MILK, "feed": "100"})["status"] == "error"
    with pytest.raises(ValidationError):
        FinancialInput.model_validate({**SAMPLE_MILK, "milk_price": "0.40"})


def test_input_metadata_exposes_unit_minimum_and_required():
    by_name = {item["name"]: item for item in list_input_metadata()}

    cows = by_name["milking_cows"]
    assert cows["type"] == "number"
    assert cows["required"] is True
    assert cows["minimum"] == 0
    assert cows["maximum"] is None
    assert cows["unit"] == "count"
    assert cows["unit"] == FIELD_UNITS["milking_cows"]
    assert "milking cows" in cows["description"].lower()

    price = by_name["milk_price"]
    assert price["required"] is True
    assert price["minimum"] == 0
    assert price["maximum"] is None
    assert price["unit"] == "EUR/litre"
    assert price["unit"] == FIELD_UNITS["milk_price"]

    feed = by_name["feed"]
    assert feed["required"] is False
    assert feed["minimum"] == 0
    assert feed["maximum"] is None
    assert feed["unit"] == "EUR/year"

    assert by_name["period"]["unit"] == "annual"
    assert by_name["period"]["type"] == "string"
    assert by_name["period"]["maximum"] is None
    assert by_name["currency"]["unit"] == "EUR"
    assert by_name["currency"]["type"] == "string"

    for item in by_name.values():
        if item["type"] == "number":
            assert item["minimum"] == 0
            assert item["maximum"] is None
        assert item["unit"] == FIELD_UNITS[item["name"]]
