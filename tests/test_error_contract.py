"""Stable machine-readable calculation error contract."""

from __future__ import annotations

from math import inf, nan

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.errors import (
    INVALID_TYPE,
    MISSING_REQUIRED,
    NEGATIVE_VALUE,
    NON_FINITE_VALUE,
    NULL_NOT_ALLOWED,
    UNKNOWN_CALCULATION,
    UNKNOWN_FIELD,
)
from farm_functions.runner import run_function

client = TestClient(app)

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}


def test_success_revenue_milk_shape_unchanged() -> None:
    result = run_function("revenue.milk", SAMPLE_MILK)
    assert result == {
        "status": "ok",
        "function": "revenue.milk",
        "result": {"amount": 200000.0, "currency": "EUR"},
    }
    assert "error" not in result
    assert "errors" not in result


def test_missing_required_needs_input_with_code() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert result["status"] == "needs_input"
    assert result["function"] == "revenue.milk"
    assert result["missing"] == [{"field": "milk_price", "unit": "EUR/litre"}]
    assert result["provided"] == ["litres_per_cow", "milking_cows"]
    assert result["error"]["code"] == MISSING_REQUIRED
    assert result["error"]["field"] == "milk_price"
    assert result["errors"] == [result["error"]]


def test_unknown_field_typo() -> None:
    result = run_function(
        "revenue.milk",
        {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_price": 0.40,
            "milk_prcie": 0.40,
        },
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == UNKNOWN_FIELD
    assert result["error"]["field"] == "milk_prcie"
    assert all(item["code"] == UNKNOWN_FIELD for item in result["errors"])


def test_cross_function_field_is_unknown_field() -> None:
    result = run_function("revenue.milk", {**SAMPLE_MILK, "feed": 80_000})
    assert result["status"] == "error"
    assert result["error"]["code"] == UNKNOWN_FIELD
    assert result["error"]["field"] == "feed"


def test_null_not_allowed() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": None},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == NULL_NOT_ALLOWED
    assert result["error"]["field"] == "milk_price"
    assert result["error"]["value"] is None


def test_negative_value() -> None:
    result = run_function("costs.total", {"feed": -1})
    assert result["status"] == "error"
    assert result["error"]["code"] == NEGATIVE_VALUE
    assert result["error"]["field"] == "feed"
    assert result["error"]["value"] == -1
    assert result["error"]["details"] == {"minimum": 0}


def test_invalid_type_string_and_bool() -> None:
    string_result = run_function("revenue.milk", {**SAMPLE_MILK, "milk_price": "0.40"})
    assert string_result["status"] == "error"
    assert string_result["error"]["code"] == INVALID_TYPE
    assert string_result["error"]["field"] == "milk_price"

    bool_result = run_function("revenue.milk", {**SAMPLE_MILK, "milking_cows": True})
    assert bool_result["status"] == "error"
    assert bool_result["error"]["code"] == INVALID_TYPE
    assert bool_result["error"]["field"] == "milking_cows"


def test_non_finite_python_values() -> None:
    nan_result = run_function("revenue.milk", {**SAMPLE_MILK, "milk_price": nan})
    assert nan_result["status"] == "error"
    assert nan_result["error"]["code"] == NON_FINITE_VALUE
    assert nan_result["error"]["field"] == "milk_price"

    inf_result = run_function("revenue.milk", {**SAMPLE_MILK, "milk_price": inf})
    assert inf_result["status"] == "error"
    assert inf_result["error"]["code"] == NON_FINITE_VALUE
    assert inf_result["error"]["field"] == "milk_price"


def test_multiple_negatives_are_deterministic() -> None:
    result = run_function(
        "pl.summary",
        {
            "milking_cows": -1,
            "litres_per_cow": 5000,
            "milk_price": 0.40,
            "feed": -2,
        },
    )
    assert result["status"] == "error"
    fields = [item["field"] for item in result["errors"]]
    assert fields == sorted(fields)
    assert {item["code"] for item in result["errors"]} == {NEGATIVE_VALUE}
    assert result["error"] == result["errors"][0]


def test_unknown_calculation_runner() -> None:
    result = run_function("does.not.exist", {})
    assert result["status"] == "error"
    assert result["error"]["code"] == UNKNOWN_CALCULATION
    assert "function" not in result
    assert result["errors"] == [result["error"]]


def test_unknown_calculation_http_404_structured() -> None:
    response = client.post("/v1/functions/does.not.exist/run", json={})
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == UNKNOWN_CALCULATION


def test_http_missing_and_unknown_field_use_codes() -> None:
    missing = client.post(
        "/v1/functions/revenue.milk/run",
        json={"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert missing.status_code == 200
    assert missing.json()["status"] == "needs_input"
    assert missing.json()["error"]["code"] == MISSING_REQUIRED

    unknown = client.post(
        "/v1/functions/revenue.milk/run",
        json={**SAMPLE_MILK, "random_field": 1},
    )
    assert unknown.status_code == 200
    assert unknown.json()["status"] == "error"
    assert unknown.json()["error"]["code"] == UNKNOWN_FIELD
    assert unknown.json()["error"]["field"] == "random_field"


def test_non_object_body_invalid_type() -> None:
    result = run_function("revenue.milk", [1, 2, 3])  # type: ignore[arg-type]
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert "field" not in result["error"]
