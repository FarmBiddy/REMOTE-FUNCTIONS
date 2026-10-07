"""OpenAPI examples (ADR-0050): one real payload per public ID, always valid."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes import load_example
from farm_functions.registry import PUBLIC_CALCULATION_IDS
from farm_functions.runner import run_function


@pytest.mark.parametrize("key", PUBLIC_CALCULATION_IDS)
def test_every_id_has_a_working_example(key):
    example = load_example(key)
    assert example, f"sample_data/examples/{key}.json is missing"
    result = run_function(key, example)
    assert result["status"] == "ok", result


def test_examples_are_published_in_openapi():
    spec = TestClient(app).get("/openapi.json").json()
    for key in PUBLIC_CALCULATION_IDS:
        body = spec["paths"][f"/v1/functions/{key}/run"]["post"]["requestBody"]
        assert body["content"]["application/json"]["example"] == load_example(key)
