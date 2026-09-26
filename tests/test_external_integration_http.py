"""External-client HTTP contract for annual pl.summary (I2).

Proves the public route a future Next.js mock will call — not the financial matrix.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs

client = TestClient(app)

_PL_SUMMARY_RUN = "/v1/functions/pl.summary/run"


def test_pl_summary_http_reference_round_trip() -> None:
    response = client.post(_PL_SUMMARY_RUN, json=load_sample_inputs())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["function"] == "pl.summary"
    result = body["result"]
    assert set(result.keys()) == {"currency", "period", "revenue", "costs", "profit", "finance"}
    assert "provenance" not in result
    assert result["currency"] == "EUR"
    assert result["period"] == "annual"
    assert result["revenue"]["total"] == 240_000.0
    assert result["revenue"]["schemes"] == 25_000.0
    assert result["costs"]["total"] == 163_000.0
    assert result["profit"]["net"] == 77_000.0
    assert result["profit"]["margin"] == 0.3208
    assert result["profit"]["margin_pct"] == 32.08
    assert result["finance"]["loan_repayments"] == 12_000.0


def test_pl_summary_http_needs_input_missing_milk_price() -> None:
    response = client.post(
        _PL_SUMMARY_RUN,
        json={"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["code"] == "missing_required"
    assert body["error"]["field"] == "milk_price"
    assert body["missing"] == [{"field": "milk_price", "unit": "EUR/litre"}]


def test_pl_summary_http_unknown_field_error() -> None:
    payload = {**load_sample_inputs(), "random_field": 1}
    response = client.post(_PL_SUMMARY_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unknown_field"
    assert body["error"]["field"] == "random_field"


def test_cors_allows_local_nextjs_origin() -> None:
    """Browser Next.js on :3000 must receive ACAO when calling the engine on :8000."""
    response = client.get("/livez", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
