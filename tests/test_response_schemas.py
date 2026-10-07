"""Typed response models (ADR-0051): every real output must match its model exactly.

Outputs come from the published examples plus the happy and all-zero payloads
of the registered-function tests, which also exercise the null branches.
"""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes import load_example
from farm_functions.registry import PUBLIC_CALCULATION_IDS, describe_function
from farm_functions.responses import OUTPUT_MODELS, envelope_model
from farm_functions.runner import run_function
from tests.test_registered_functions import _happy_payload, _zero_payload

client = TestClient(app)


def _payloads(key):
    return {"example": load_example(key), "happy": _happy_payload(key), "zero": _zero_payload(key)}


def test_every_id_has_an_output_model():
    assert set(OUTPUT_MODELS) == set(PUBLIC_CALCULATION_IDS)


@pytest.mark.parametrize("key", PUBLIC_CALCULATION_IDS)
def test_real_outputs_match_their_model_exactly(key):
    model = OUTPUT_MODELS[key]
    for label, payload in _payloads(key).items():
        result = run_function(key, payload)
        assert result["status"] == "ok", (label, result)
        # extra="forbid" catches new keys; the round trip catches missing / retyped ones.
        assert model.model_validate(result["result"]).model_dump(by_alias=True) == result["result"], label


@pytest.mark.parametrize("key", PUBLIC_CALCULATION_IDS)
def test_every_envelope_kind_matches(key):
    envelope = envelope_model(key)
    for payload in (load_example(key), {}, {"not_a_field": 1}):
        envelope.model_validate(run_function(key, payload))


def test_openapi_publishes_typed_responses():
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    for key in PUBLIC_CALCULATION_IDS:
        response = spec["paths"][f"/v1/functions/{key}/run"]["post"]["responses"]["200"]
        ref = response["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
        assert ref.endswith("Response") and len(schemas[ref]["anyOf"]) == 3, key


def test_discovery_includes_output_schema():
    schema = describe_function("bs.summary")["output_schema"]
    assert set(schema["properties"]) == {"currency", "as_of", "assets", "liabilities", "net_worth", "ratios"}
    assert "from" in describe_function("pl.net")["output_schema"]["properties"]
