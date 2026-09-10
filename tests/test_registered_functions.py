"""Behavior matrix: every registered function gets happy-path and edge-case coverage."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import (
    FUNCTIONS,
    INPUT_MODELS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
)
from farm_functions.runner import run_function
from farm_functions.schemas import FIELD_UNITS, missing_field_entry

client = TestClient(app)

FUNCTION_KEYS = sorted(FUNCTIONS.keys())

SAMPLE_MILK = {
    "milking_cows": 100,
    "litres_per_cow": 5000,
    "milk_price": 0.40,
}

SAMPLE_SCHEMES = {"biss": 20_000, "acres": 5_000, "other_grants": 0}
SAMPLE_OTHER = {"cattle_sales": 15_000, "lamb_sales": 0, "wool": 0, "other": 0}
SAMPLE_COSTS = {
    "feed": 80_000,
    "fertiliser": 15_000,
    "vet": 5_000,
    "contractor": 10_000,
    "labour": 40_000,
    "insurance": 4_000,
    "fuel": 6_000,
    "electricity": 3_000,
}
SAMPLE_PROFIT_TOTALS = {"revenue": 240_000, "costs": 163_000}


def _happy_payload(key: str) -> dict:
    """Sample-farm-style inputs for a registered function."""
    if key == "revenue.milk":
        return dict(SAMPLE_MILK)
    if key == "revenue.schemes":
        return dict(SAMPLE_SCHEMES)
    if key == "revenue.other":
        return dict(SAMPLE_OTHER)
    if key == "revenue.total":
        return {**SAMPLE_MILK, **SAMPLE_SCHEMES, **SAMPLE_OTHER}
    if key == "costs.total":
        return dict(SAMPLE_COSTS)
    if key in ("profit.net", "profit.margin"):
        return dict(SAMPLE_PROFIT_TOTALS)
    if key == "pl.summary":
        return load_sample_inputs()
    raise AssertionError(f"No happy payload for {key}")


def _required_only_payload(key: str) -> dict:
    """Required fields only (optionals omitted → default 0)."""
    required = REQUIRED_FIELDS[key]
    if not required:
        return {}
    full = _happy_payload(key)
    return {name: full[name] for name in required}


def _zero_payload(key: str) -> dict:
    """All known fields set explicitly to 0."""
    known = REQUIRED_FIELDS[key] + OPTIONAL_FIELDS[key]
    return {name: 0 for name in known}


def _assert_ok_money(result: dict, amount: float) -> None:
    assert result["status"] == "ok"
    assert result["result"]["amount"] == amount
    assert result["result"]["currency"] == "EUR"


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_happy_path(key: str) -> None:
    payload = _happy_payload(key)
    result = run_function(key, payload)
    assert result["status"] == "ok"
    assert result["function"] == key

    if key == "revenue.milk":
        _assert_ok_money(result, 200_000)
    elif key == "revenue.schemes":
        _assert_ok_money(result, 25_000)
    elif key == "revenue.other":
        _assert_ok_money(result, 15_000)
    elif key == "revenue.total":
        _assert_ok_money(result, 240_000)
    elif key == "costs.total":
        _assert_ok_money(result, 163_000)
    elif key == "profit.net":
        _assert_ok_money(result, 77_000)
    elif key == "profit.margin":
        body = result["result"]
        assert body["margin"] == 0.3208
        assert body["margin_pct"] == 32.08
        assert body["profit"] == 77_000
        assert body["revenue"] == 240_000
        assert body["costs"] == 163_000
        assert body["currency"] == "EUR"
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 25_000
        assert body["revenue"]["other"] == 15_000
        assert body["revenue"]["total"] == 240_000
        assert body["costs"]["total"] == 163_000
        assert body["profit"]["net"] == 77_000
        assert body["profit"]["margin_pct"] == 32.08
        assert body["finance"]["loan_repayments"] == 12_000
        assert "loan_repayments" not in body["costs"]["lines"]


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_required_only_optionals_default_to_zero(key: str) -> None:
    payload = _required_only_payload(key)
    result = run_function(key, payload)
    assert result["status"] == "ok", result

    if key == "revenue.milk":
        _assert_ok_money(result, 200_000)
    elif key == "revenue.schemes":
        _assert_ok_money(result, 0)
    elif key == "revenue.other":
        _assert_ok_money(result, 0)
    elif key == "revenue.total":
        _assert_ok_money(result, 200_000)  # milk only; schemes/other omitted
    elif key == "costs.total":
        _assert_ok_money(result, 0)
    elif key == "profit.net":
        _assert_ok_money(result, 77_000)
    elif key == "profit.margin":
        assert result["result"]["profit"] == 77_000
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 0
        assert body["revenue"]["other"] == 0
        assert body["costs"]["total"] == 0
        assert body["profit"]["net"] == 200_000
        assert body["finance"]["loan_repayments"] == 0


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_explicit_zeros_are_ok(key: str) -> None:
    result = run_function(key, _zero_payload(key))
    assert result["status"] == "ok", result

    if key in (
        "revenue.milk",
        "revenue.schemes",
        "revenue.other",
        "revenue.total",
        "costs.total",
        "profit.net",
    ):
        _assert_ok_money(result, 0)
    elif key == "profit.margin":
        assert result["result"]["margin"] == 0
        assert result["result"]["margin_pct"] == 0
        assert result["result"]["profit"] == 0
    elif key == "pl.summary":
        assert result["result"]["revenue"]["total"] == 0
        assert result["result"]["costs"]["total"] == 0
        assert result["result"]["profit"]["net"] == 0


def _missing_required_cases() -> list[tuple[str, str, dict]]:
    cases: list[tuple[str, str, dict]] = []
    for key in FUNCTION_KEYS:
        required = REQUIRED_FIELDS[key]
        if not required:
            continue
        base = _required_only_payload(key)
        for field in required:
            payload = {k: v for k, v in base.items() if k != field}
            cases.append((key, field, payload))
    return cases


@pytest.mark.parametrize("key,field,payload", _missing_required_cases())
def test_missing_each_required_field(key: str, field: str, payload: dict) -> None:
    result = run_function(key, payload)
    assert result["status"] == "needs_input"
    assert result["function"] == key
    assert missing_field_entry(field) in result["missing"]
    assert result["missing"] == [
        missing_field_entry(f) for f in REQUIRED_FIELDS[key] if f not in payload
    ]
    for item in result["missing"]:
        assert item["unit"] == FIELD_UNITS[item["field"]]


def _assert_unknown_field_error(result: dict, *fields: str) -> None:
    assert result["status"] == "error"
    assert result["message"] == "One or more values are invalid."
    assert [item["field"] for item in result["errors"]] == sorted(fields)
    assert all(item["code"] == "unknown_field" for item in result["errors"])
    assert result["error"] == result["errors"][0]


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_extra_unknown_fields_rejected(key: str) -> None:
    payload = {**_happy_payload(key), "not_a_real_field": 999, "farm_id": "demo"}
    result = run_function(key, payload)
    _assert_unknown_field_error(result, "farm_id", "not_a_real_field")


def test_revenue_milk_valid_payload_unchanged() -> None:
    result = run_function("revenue.milk", SAMPLE_MILK)
    _assert_ok_money(result, 200_000)


def test_revenue_milk_missing_milk_price_needs_input() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert result["status"] == "needs_input"
    assert result["missing"] == [missing_field_entry("milk_price")]


def test_revenue_milk_typo_field_is_error() -> None:
    result = run_function(
        "revenue.milk",
        {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_prcie": 0.40,
        },
    )
    _assert_unknown_field_error(result, "milk_prcie")


def test_revenue_milk_random_field_is_error() -> None:
    result = run_function("revenue.milk", {**SAMPLE_MILK, "random_field": 1})
    _assert_unknown_field_error(result, "random_field")


def test_revenue_milk_rejects_field_from_wrong_contract() -> None:
    result = run_function("revenue.milk", {**SAMPLE_MILK, "feed": 80_000})
    _assert_unknown_field_error(result, "feed")


def test_pl_summary_unknown_cost_is_error() -> None:
    result = run_function("pl.summary", {**load_sample_inputs(), "unknown_cost": 1})
    _assert_unknown_field_error(result, "unknown_cost")


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_empty_body(key: str) -> None:
    result = run_function(key, {})
    required = REQUIRED_FIELDS[key]
    if required:
        assert result["status"] == "needs_input"
        assert result["missing"] == [missing_field_entry(f) for f in required]
        assert result["provided"] == []
    else:
        assert result["status"] == "ok"
        _assert_ok_money(result, 0)


def test_registry_maps_are_complete() -> None:
    keys = set(FUNCTIONS)
    assert keys == set(REQUIRED_FIELDS)
    assert keys == set(OPTIONAL_FIELDS)
    assert keys == set(INPUT_MODELS)
    for key in keys:
        spec = FUNCTIONS[key]
        assert spec.id == key
        assert spec.required == REQUIRED_FIELDS[key]
        assert spec.optional == OPTIONAL_FIELDS[key]
        assert spec.input_model is INPUT_MODELS[key]


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_http_smoke_matches_runner(key: str) -> None:
    payload = _happy_payload(key)
    via_runner = run_function(key, payload)
    response = client.post(f"/v1/functions/{key}/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == via_runner["status"]
    assert body["status"] == "ok"
    assert body["result"] == via_runner["result"]


def test_openapi_lists_every_registered_function_route() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for key in FUNCTION_KEYS:
        assert f"/v1/functions/{key}/run" in paths
    assert "/v1/functions/{name}/run" not in paths
