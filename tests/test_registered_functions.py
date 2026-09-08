"""Behavior matrix: every registered function gets happy-path and edge-case coverage."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import FUNCTIONS
from farm_functions.runner import run_function
from farm_functions.schemas import (
    FIELD_UNITS,
    INPUT_MODELS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    missing_field_entry,
)

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
    "loan_repayments": 12_000,
    "fuel": 6_000,
    "electricity": 3_000,
}
SAMPLE_PROFIT_TOTALS = {"revenue": 240_000, "costs": 175_000}


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
        _assert_ok_money(result, 175_000)
    elif key == "profit.net":
        _assert_ok_money(result, 65_000)
    elif key == "profit.margin":
        body = result["result"]
        assert body["margin"] == 0.2708
        assert body["margin_pct"] == 27.08
        assert body["profit"] == 65_000
        assert body["revenue"] == 240_000
        assert body["costs"] == 175_000
        assert body["currency"] == "EUR"
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 25_000
        assert body["revenue"]["other"] == 15_000
        assert body["revenue"]["total"] == 240_000
        assert body["costs"]["total"] == 175_000
        assert body["profit"]["net"] == 65_000
        assert body["profit"]["margin_pct"] == 27.08


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
        _assert_ok_money(result, 65_000)
    elif key == "profit.margin":
        assert result["result"]["profit"] == 65_000
    elif key == "pl.summary":
        body = result["result"]
        assert body["revenue"]["milk"] == 200_000
        assert body["revenue"]["schemes"] == 0
        assert body["revenue"]["other"] == 0
        assert body["costs"]["total"] == 0
        assert body["profit"]["net"] == 200_000


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


@pytest.mark.parametrize("key", FUNCTION_KEYS)
def test_extra_unknown_fields_ignored(key: str) -> None:
    payload = {**_happy_payload(key), "not_a_real_field": 999, "farm_id": "demo"}
    result = run_function(key, payload)
    assert result["status"] == "ok"
    # Same outcome as happy path without extras
    baseline = run_function(key, _happy_payload(key))
    assert result["result"] == baseline["result"]


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
        assert spec.required == REQUIRED_FIELDS[key]
        assert spec.optional == OPTIONAL_FIELDS[key]


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
