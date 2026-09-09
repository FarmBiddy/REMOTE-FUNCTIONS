"""Domain / catalogue / discovery / HTTP alignment regression checks."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.registry import (
    FUNCTIONS,
    PUBLIC_CALCULATION_IDS,
    REQUIRED_FIELDS,
    list_functions,
)

client = TestClient(app)

_OPENAPI_RUN_PATH = re.compile(r"^/v1/functions/([^/]+)/run$")


def _openapi_run_ids(paths: dict) -> set[str]:
    ids: set[str] = set()
    for path in paths:
        match = _OPENAPI_RUN_PATH.match(path)
        if match and "{" not in match.group(1):
            ids.add(match.group(1))
    return ids


def test_public_ids_match_discovery_and_openapi_routes() -> None:
    catalogue_ids = set(PUBLIC_CALCULATION_IDS)
    discovery_ids = {item["key"] for item in list_functions()}
    openapi_ids = _openapi_run_ids(client.get("/openapi.json").json()["paths"])
    assert catalogue_ids == discovery_ids == openapi_ids
    assert len(catalogue_ids) == 8


def test_discovery_fields_match_catalogue() -> None:
    for item in list_functions():
        spec = FUNCTIONS[item["key"]]
        assert item["description"] == spec.description
        assert item["required"] == list(spec.required)
        assert item["optional"] == list(spec.optional)


def test_http_discovery_equals_list_functions() -> None:
    response = client.get("/v1/functions")
    assert response.status_code == 200
    assert response.json()["functions"] == list_functions()


def test_openapi_required_fields_match_registry() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for calculation_id in PUBLIC_CALCULATION_IDS:
        path = f"/v1/functions/{calculation_id}/run"
        schema = paths[path]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert set(schema.get("required", [])) == set(REQUIRED_FIELDS[calculation_id])
