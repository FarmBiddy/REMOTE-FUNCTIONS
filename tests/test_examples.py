"""OpenAPI examples (ADR-0050): one real payload per public ID, always valid,
plus optional named variants (``<id>.<name>.json``)."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes import load_example, load_example_variants
from farm_functions.registry import PUBLIC_CALCULATION_IDS
from farm_functions.runner import run_function

VARIANTS = [(key, name) for key in PUBLIC_CALCULATION_IDS for name in load_example_variants(key)]


@pytest.mark.parametrize("key", PUBLIC_CALCULATION_IDS)
def test_every_id_has_a_working_example(key):
    example = load_example(key)
    assert example, f"sample_data/examples/{key}.json is missing"
    result = run_function(key, example)
    assert result["status"] == "ok", result


@pytest.mark.parametrize(("key", "name"), VARIANTS)
def test_every_variant_works(key, name):
    result = run_function(key, load_example_variants(key)[name])
    assert result["status"] == "ok", result


def test_examples_are_published_in_openapi():
    spec = TestClient(app).get("/openapi.json").json()
    for key in PUBLIC_CALCULATION_IDS:
        content = spec["paths"][f"/v1/functions/{key}/run"]["post"]["requestBody"]["content"]["application/json"]
        variants = load_example_variants(key)
        if variants:
            assert content["examples"]["default"]["value"] == load_example(key)
            assert {n: e["value"] for n, e in content["examples"].items() if n != "default"} == variants
        else:
            assert content["example"] == load_example(key)


def test_plan_projection_has_partnership_and_flat_rate_examples():
    assert "partnership" in load_example_variants("plan.projection")
    assert load_example("plan.projection")["tax_profile"]["vat_registered"] is False
