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
    assert body["missing"] == ["milk_price"]


def test_demo_pl_summary():
    response = client.post("/v1/demo/pl-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result"]["profit"]["net"] == 65_000
