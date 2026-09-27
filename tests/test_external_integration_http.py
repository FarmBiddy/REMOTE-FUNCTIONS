"""External-client HTTP contract for annual pl.summary (I2) and monthly pl.monthly (P1.4).

Proves the public routes a Next.js mock will call — not the full financial matrix.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.loaders.json_loader import load_sample_inputs

client = TestClient(app)

_PL_SUMMARY_RUN = "/v1/functions/pl.summary/run"
_PL_MONTHLY_RUN = "/v1/functions/pl.monthly/run"

# Locked P1.2/P1.3 monthly reference — not derived from annual ÷ 12.
_MONTHLY_REFERENCE = {
    "year": 2026,
    "month": 3,
    "milk_litres": 40_000,
    "milk_price": 0.40,
    "biss": 2_000,
    "acres": 500,
    "other_grants": 0,
    "cattle_sales": 1_000,
    "land_leasing_income": 0,
    "other": 0,
    "feed": 5_000,
    "fertiliser": 1_000,
    "loan_repayments": 1_500,
}


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


def test_pl_monthly_http_reference_round_trip() -> None:
    response = client.post(_PL_MONTHLY_RUN, json=_MONTHLY_REFERENCE)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["function"] == "pl.monthly"
    result = body["result"]
    assert set(result.keys()) == {"currency", "period", "revenue", "costs", "profit", "finance"}
    assert "provenance" not in result
    assert result["currency"] == "EUR"
    assert result["period"] == {"kind": "month", "year": 2026, "month": 3}
    assert result["revenue"]["milk"] == 16_000.0
    assert result["revenue"]["schemes"] == 2_500.0
    assert result["revenue"]["other"] == 1_000.0
    assert result["revenue"]["total"] == 19_500.0
    assert result["costs"]["total"] == 6_000.0
    assert result["profit"]["net"] == 13_500.0
    assert result["profit"]["margin"] == 0.6923
    assert result["profit"]["margin_pct"] == 69.23
    assert result["finance"]["loan_repayments"] == 1_500.0


def test_pl_monthly_http_period_identity_returned() -> None:
    payload = {**_MONTHLY_REFERENCE, "year": 2024, "month": 11}
    response = client.post(_PL_MONTHLY_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["result"]["period"] == {"kind": "month", "year": 2024, "month": 11}
    assert body["result"]["profit"]["net"] == 13_500.0


def test_pl_monthly_http_missing_year() -> None:
    payload = {k: v for k, v in _MONTHLY_REFERENCE.items() if k != "year"}
    response = client.post(_PL_MONTHLY_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["code"] == "missing_required"
    assert body["error"]["field"] == "year"
    assert {"field": "year", "unit": "year"} in body["missing"]


def test_pl_monthly_http_missing_month() -> None:
    payload = {k: v for k, v in _MONTHLY_REFERENCE.items() if k != "month"}
    response = client.post(_PL_MONTHLY_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["code"] == "missing_required"
    assert body["error"]["field"] == "month"
    assert {"field": "month", "unit": "month"} in body["missing"]


def test_pl_monthly_http_invalid_month() -> None:
    response = client.post(
        _PL_MONTHLY_RUN,
        json={**_MONTHLY_REFERENCE, "month": 13},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "invalid_type"
    assert body["error"]["field"] == "month"


def test_pl_monthly_http_missing_milk_litres() -> None:
    payload = {k: v for k, v in _MONTHLY_REFERENCE.items() if k != "milk_litres"}
    response = client.post(_PL_MONTHLY_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_input"
    assert body["error"]["code"] == "missing_required"
    assert body["error"]["field"] == "milk_litres"
    assert {"field": "milk_litres", "unit": "litres"} in body["missing"]


def test_pl_monthly_http_negative_value() -> None:
    response = client.post(
        _PL_MONTHLY_RUN,
        json={**_MONTHLY_REFERENCE, "feed": -1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "negative_value"
    assert body["error"]["field"] == "feed"


def test_pl_monthly_http_unknown_field() -> None:
    response = client.post(
        _PL_MONTHLY_RUN,
        json={**_MONTHLY_REFERENCE, "litres_per_cow": 5000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "unknown_field"
    assert body["error"]["field"] == "litres_per_cow"


def test_pl_monthly_http_loan_only_changes_finance() -> None:
    base = client.post(_PL_MONTHLY_RUN, json=_MONTHLY_REFERENCE).json()["result"]
    high = client.post(
        _PL_MONTHLY_RUN,
        json={**_MONTHLY_REFERENCE, "loan_repayments": 9_999},
    ).json()["result"]
    assert high["finance"]["loan_repayments"] == 9_999.0
    assert high["costs"]["total"] == base["costs"]["total"]
    assert high["profit"]["net"] == base["profit"]["net"]
    assert high["profit"]["margin"] == base["profit"]["margin"]
    assert high["profit"]["margin_pct"] == base["profit"]["margin_pct"]


def test_annual_and_monthly_ids_resolve_independently() -> None:
    annual = client.post(_PL_SUMMARY_RUN, json=load_sample_inputs())
    monthly = client.post(_PL_MONTHLY_RUN, json=_MONTHLY_REFERENCE)
    assert annual.json()["function"] == "pl.summary"
    assert monthly.json()["function"] == "pl.monthly"
    assert annual.json()["result"]["period"] == "annual"
    assert monthly.json()["result"]["period"]["kind"] == "month"
    assert annual.json()["result"]["profit"]["net"] == 77_000.0
    assert monthly.json()["result"]["profit"]["net"] == 13_500.0


def test_unknown_function_id_unchanged() -> None:
    response = client.post("/v1/functions/does.not.exist/run", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_calculation"


def test_cors_allows_local_nextjs_origin() -> None:
    """Browser Next.js on :3000 must receive ACAO when calling the engine on :8000."""
    response = client.get("/livez", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_allows_local_nextjs_origin_on_monthly_post() -> None:
    response = client.post(
        _PL_MONTHLY_RUN,
        json=_MONTHLY_REFERENCE,
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
