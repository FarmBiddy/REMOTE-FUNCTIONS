from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_list_functions():
    response = client.get("/v1/functions")
    assert response.status_code == 200
    keys = [item["key"] for item in response.json()["functions"]]
    assert "profit.margin" in keys
    assert "revenue.milk" in keys


def test_run_unknown_function():
    response = client.post("/v1/functions/does.not.exist/run", json={})
    assert response.status_code == 404


def test_run_asks_for_missing_numbers():
    response = client.post(
        "/v1/functions/revenue.milk/run",
        json={"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["missing"] == [{"field": "milk_price", "unit": "EUR/litre"}]


def test_run_rejects_unknown_fields():
    response = client.post(
        "/v1/functions/revenue.milk/run",
        json={
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_price": 0.40,
            "random_field": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["details"] == [{"field": "random_field", "reason": "unknown field"}]


def test_demo_pl_summary():
    response = client.post("/v1/demo/pl-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result"]["profit"]["net"] == 65_000


def test_pl_summary_http_shape_has_no_provenance():
    result = client.post("/v1/demo/pl-summary").json()["result"]
    assert set(result.keys()) == {"currency", "period", "revenue", "costs", "profit"}
    assert "provenance" not in result
    assert set(result["revenue"].keys()) == {"milk", "schemes", "other", "total"}
    assert set(result["costs"].keys()) == {"lines", "total"}
    assert set(result["profit"].keys()) == {"net", "margin", "margin_pct"}


def test_openapi_exposes_typed_function_inputs():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/functions/revenue.milk/run" in paths
    assert "/v1/functions/{name}/run" not in paths

    request_body = paths["/v1/functions/revenue.milk/run"]["post"]["requestBody"]
    schema = request_body["content"]["application/json"]["schema"]
    assert schema["properties"]["milking_cows"]["type"] == "number"
    assert schema["properties"]["litres_per_cow"]["type"] == "number"
    assert schema["properties"]["milk_price"]["type"] == "number"
    assert set(schema["required"]) == {
        "milking_cows",
        "litres_per_cow",
        "milk_price",
    }
