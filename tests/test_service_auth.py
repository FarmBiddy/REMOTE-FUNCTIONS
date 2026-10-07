"""Service-to-service token, readiness and safe binding (ADR-0049)."""

import pytest
from fastapi.testclient import TestClient

import run_server
from api.app import app

RUN = "/v1/functions/revenue.schemes/run"


@pytest.fixture
def keyed(monkeypatch):
    monkeypatch.setenv("ENGINE_API_KEY", "s3cret-key")
    return TestClient(app)


def test_open_without_a_key(monkeypatch):
    monkeypatch.delenv("ENGINE_API_KEY", raising=False)
    assert TestClient(app).post(RUN, json={"biss": 1}).json()["status"] == "ok"


def test_key_required_on_v1_routes(keyed):
    for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": "s3cret-key"}):
        response = keyed.post(RUN, json={"biss": 1}, headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
    assert keyed.get("/v1/functions").status_code == 401
    ok = keyed.post(RUN, json={"biss": 1}, headers={"Authorization": "Bearer s3cret-key"})
    assert ok.status_code == 200 and ok.json()["status"] == "ok"


def test_probes_stay_open(keyed):
    assert keyed.get("/livez").status_code == 200
    assert keyed.get("/health").status_code == 200


def test_cors_preflight_is_not_blocked(keyed):
    preflight = keyed.options(
        RUN,
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200


def test_readyz_follows_the_lifespan():
    with TestClient(app) as client:
        assert client.get("/readyz").json() == {"ready": True}
    assert TestClient(app).get("/readyz").status_code == 503


def test_refuses_to_expose_an_open_engine(monkeypatch):
    calls = []
    monkeypatch.setattr(run_server.uvicorn, "run", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(run_server, "_load_dotenv_if_present", lambda: None)
    monkeypatch.setenv("ENGINE_HOST", "0.0.0.0")
    monkeypatch.delenv("ENGINE_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        run_server.main()
    monkeypatch.setenv("ENGINE_API_KEY", "k")
    run_server.main()
    assert calls == [{"host": "0.0.0.0", "port": 8000}]
    monkeypatch.delenv("ENGINE_API_KEY")
    monkeypatch.setenv("ENGINE_HOST", "127.0.0.1")
    run_server.main()  # loopback without a key is fine for local development
    assert calls[-1]["host"] == "127.0.0.1"
