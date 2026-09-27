"""P2.4 HTTP contract for pl.months (ADR-0021) over Domain P2.1 / P2.2."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.domain import (
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    YtdDairyStatementModel,
    calculate_ytd_dairy_statement,
)
from farm_functions.errors import INVALID_TYPE, MISSING_REQUIRED, NEGATIVE_VALUE, NULL_NOT_ALLOWED
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import list_functions
from farm_functions.runner import run_function
from farm_functions.schemas import MonthlyDairyFinancialInput

client = TestClient(app)

_PL_MONTHS_RUN = "/v1/functions/pl.months/run"
_PL_SUMMARY_RUN = "/v1/functions/pl.summary/run"
_PL_MONTHLY_RUN = "/v1/functions/pl.monthly/run"

# Hand-checkable Jan–Mar fixture (literal expecteds; avg margin ≠ YTD margin).
YTD_REV = 1_300.0
YTD_COST = 960.0
YTD_SURPLUS = 340.0
YTD_MARGIN = 0.2615
YTD_MARGIN_PCT = 26.15
YTD_LOANS = 30.0
AVG_MONTHLY_MARGINS = (0.90 + 0.10 + 0.75) / 3.0

MARCH_REFERENCE = {
    "year": 2026,
    "month": 3,
    "milk_litres": 40_000,
    "milk_price": 0.40,
    "biss": 2_000,
    "acres": 500,
    "cattle_sales": 1_000,
    "feed": 5_000,
    "fertiliser": 1_000,
    "loan_repayments": 1_500,
}


def _hand_month(
    year: int,
    month: int,
    *,
    revenue: float,
    cost: float,
    loan: float = 0.0,
) -> dict:
    return {
        "year": year,
        "month": month,
        "milk_litres": revenue,
        "milk_price": 1.0,
        "biss": 0,
        "acres": 0,
        "other_grants": 0,
        "cattle_sales": 0,
        "land_leasing_income": 0,
        "other": 0,
        "feed": cost,
        "fertiliser": 0,
        "loan_repayments": loan,
    }


def _jan_mar_months() -> list[dict]:
    return [
        _hand_month(2026, 1, revenue=100.0, cost=10.0, loan=5.0),
        _hand_month(2026, 2, revenue=1_000.0, cost=900.0, loan=10.0),
        _hand_month(2026, 3, revenue=200.0, cost=50.0, loan=15.0),
    ]


def test_pl_months_registered_and_discoverable() -> None:
    keys = {item["key"] for item in list_functions()}
    assert "pl.months" in keys
    entry = next(item for item in list_functions() if item["key"] == "pl.months")
    assert entry["required"] == ["months"]
    assert entry["optional"] == ["ytd"]
    response = client.get("/v1/functions")
    assert response.status_code == 200
    assert "pl.months" in {item["key"] for item in response.json()["functions"]}


def test_multiple_months_http_round_trip() -> None:
    payload = {"months": _jan_mar_months()}
    via_runner = run_function("pl.months", payload)
    response = client.post(_PL_MONTHS_RUN, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body == via_runner
    assert body["status"] == "ok"
    assert body["function"] == "pl.months"
    assert len(body["result"]["months"]) == 3


def test_chronological_monthly_response() -> None:
    payload = {
        "months": [
            _hand_month(2026, 3, revenue=200.0, cost=50.0),
            _hand_month(2026, 1, revenue=100.0, cost=10.0),
            _hand_month(2026, 2, revenue=1_000.0, cost=900.0),
        ]
    }
    result = run_function("pl.months", payload)
    months = [m["period"]["month"] for m in result["result"]["months"]]
    assert months == [1, 2, 3]


def test_sparse_series_without_ytd() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [
                _hand_month(2026, 1, revenue=100.0, cost=10.0),
                _hand_month(2026, 3, revenue=200.0, cost=50.0),
            ]
        },
    )
    assert result["status"] == "ok"
    assert result["result"]["ytd"] is None
    assert [m["period"]["month"] for m in result["result"]["months"]] == [1, 3]


def test_cross_year_sparse_without_ytd() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [
                _hand_month(2025, 12, revenue=100.0, cost=10.0),
                _hand_month(2026, 1, revenue=200.0, cost=50.0),
            ]
        },
    )
    assert result["status"] == "ok"
    assert result["result"]["ytd"] is None
    periods = [(m["period"]["year"], m["period"]["month"]) for m in result["result"]["months"]]
    assert periods == [(2025, 12), (2026, 1)]


def test_no_ytd_key_and_null_ytd_are_null() -> None:
    months = _jan_mar_months()
    omitted = run_function("pl.months", {"months": months})
    with_null = run_function("pl.months", {"months": months, "ytd": None})
    assert "ytd" in omitted["result"]
    assert omitted["result"]["ytd"] is None
    assert with_null["result"]["ytd"] is None


def test_jan_mar_ytd_hand_totals() -> None:
    result = run_function(
        "pl.months",
        {
            "months": _jan_mar_months(),
            "ytd": {"year": 2026, "as_of_month": 3},
        },
    )
    assert result["status"] == "ok"
    body = result["result"]
    assert len(body["months"]) == 3
    ytd = body["ytd"]
    assert ytd is not None
    assert ytd["period"]["kind"] == "ytd"
    assert ytd["period"]["months_included"] == [1, 2, 3]
    assert ytd["revenue"]["total"] == YTD_REV
    assert ytd["costs"]["total"] == YTD_COST
    assert ytd["profit"]["net"] == YTD_SURPLUS
    assert ytd["profit"]["margin"] == YTD_MARGIN
    assert ytd["profit"]["margin_pct"] == YTD_MARGIN_PCT
    assert ytd["finance"]["loan_repayments"] == YTD_LOANS
    assert ytd["profit"]["margin"] != pytest.approx(AVG_MONTHLY_MARGINS)
    assert abs(ytd["profit"]["margin"] - AVG_MONTHLY_MARGINS) > 0.2


def test_ytd_matches_domain_calculator() -> None:
    months_payload = _jan_mar_months()
    http = run_function(
        "pl.months",
        {"months": months_payload, "ytd": {"year": 2026, "as_of_month": 3}},
    )
    envelopes = [
        MonthlyDairyStatementModel(
            period=MonthlyPeriodIdentity(year=m["year"], month=m["month"]),
            inputs=MonthlyDairyFinancialInput.model_validate(
                {k: v for k, v in m.items() if k not in ("year", "month")}
            ),
        )
        for m in months_payload
    ]
    domain = calculate_ytd_dairy_statement(
        YtdDairyStatementModel(year=2026, as_of_month=3, months=envelopes)
    )
    assert http["result"]["ytd"] == domain.model_dump()


def test_duplicate_period_error() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [
                _hand_month(2026, 1, revenue=100.0, cost=10.0),
                _hand_month(2026, 1, revenue=200.0, cost=20.0),
            ]
        },
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert result["error"]["details"]["reason"] == "duplicate_period"


def test_empty_months_error() -> None:
    result = run_function("pl.months", {"months": []})
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert result["error"]["details"]["reason"] == "empty_months"


def test_nested_missing_required_field() -> None:
    result = run_function(
        "pl.months",
        {"months": [{"year": 2026, "month": 1, "milk_price": 1.0}]},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == MISSING_REQUIRED
    assert result["error"]["field"] == "milk_litres"


def test_negative_monthly_value() -> None:
    result = run_function(
        "pl.months",
        {"months": [_hand_month(2026, 1, revenue=100.0, cost=-1.0)]},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == NEGATIVE_VALUE


def test_null_nested_financial_value() -> None:
    month = _hand_month(2026, 1, revenue=100.0, cost=10.0)
    month["feed"] = None
    result = run_function("pl.months", {"months": [month]})
    assert result["status"] == "error"
    assert result["error"]["code"] == NULL_NOT_ALLOWED


def test_invalid_calendar_month() -> None:
    result = run_function(
        "pl.months",
        {"months": [_hand_month(2026, 13, revenue=100.0, cost=10.0)]},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE


def test_ytd_missing_january() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [_hand_month(2026, 2, revenue=100.0, cost=10.0)],
            "ytd": {"year": 2026, "as_of_month": 2},
        },
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert result["error"]["details"]["reason"] == "ytd_incomplete"


def test_ytd_intermediate_gap() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [
                _hand_month(2026, 1, revenue=100.0, cost=10.0),
                _hand_month(2026, 3, revenue=200.0, cost=50.0),
            ],
            "ytd": {"year": 2026, "as_of_month": 3},
        },
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert result["error"]["details"]["reason"] == "ytd_incomplete"


def test_wrong_ytd_year() -> None:
    result = run_function(
        "pl.months",
        {
            "months": [_hand_month(2026, 1, revenue=100.0, cost=10.0)],
            "ytd": {"year": 2025, "as_of_month": 1},
        },
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == INVALID_TYPE
    assert result["error"]["details"]["reason"] == "ytd_year_mismatch"


def test_finance_separation_on_ytd() -> None:
    result = run_function(
        "pl.months",
        {
            "months": _jan_mar_months(),
            "ytd": {"year": 2026, "as_of_month": 3},
        },
    )
    ytd = result["result"]["ytd"]
    assert ytd["finance"]["loan_repayments"] == YTD_LOANS
    assert ytd["costs"]["total"] == YTD_COST
    assert ytd["profit"]["net"] == YTD_SURPLUS
    assert "loan_repayments" not in ytd["costs"]["lines"]


def test_annual_pl_summary_reference_unchanged() -> None:
    result = run_function("pl.summary", load_sample_inputs())
    assert result["status"] == "ok"
    body = result["result"]
    assert body["revenue"]["total"] == 240_000
    assert body["costs"]["total"] == 163_000
    assert body["profit"]["net"] == 77_000
    assert body["profit"]["margin"] == 0.3208
    assert body["profit"]["margin_pct"] == 32.08
    assert body["finance"]["loan_repayments"] == 12_000


def test_monthly_pl_monthly_reference_unchanged() -> None:
    result = run_function("pl.monthly", MARCH_REFERENCE)
    assert result["status"] == "ok"
    body = result["result"]
    assert body["revenue"]["total"] == 19_500
    assert body["costs"]["total"] == 6_000
    assert body["profit"]["net"] == 13_500
    assert body["profit"]["margin"] == 0.6923
    assert body["profit"]["margin_pct"] == 69.23
    assert body["finance"]["loan_repayments"] == 1_500


def test_cors_allows_local_nextjs_on_pl_months() -> None:
    response = client.post(
        _PL_MONTHS_RUN,
        json={"months": [_hand_month(2026, 1, revenue=100.0, cost=10.0)]},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_unknown_function_behaviour_unchanged() -> None:
    response = client.post("/v1/functions/does.not.exist/run", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_calculation"


def test_response_is_domain_dump_shape() -> None:
    """Money nests match Domain serialization — no chart / UI formula surface."""
    result = run_function(
        "pl.months",
        {
            "months": _jan_mar_months(),
            "ytd": {"year": 2026, "as_of_month": 3},
        },
    )
    month0 = result["result"]["months"][0]
    assert set(month0.keys()) == {
        "currency",
        "period",
        "revenue",
        "costs",
        "profit",
        "finance",
    }
    ytd = result["result"]["ytd"]
    assert set(ytd.keys()) == {
        "currency",
        "period",
        "revenue",
        "costs",
        "profit",
        "finance",
    }
    assert "chart" not in result["result"]
    assert "series" not in result["result"]


def test_annual_and_monthly_http_endpoints_still_ok() -> None:
    annual = client.post(_PL_SUMMARY_RUN, json=load_sample_inputs())
    monthly = client.post(_PL_MONTHLY_RUN, json=MARCH_REFERENCE)
    assert annual.status_code == 200
    assert monthly.status_code == 200
    assert annual.json()["result"]["profit"]["net"] == 77_000
    assert monthly.json()["result"]["profit"]["net"] == 13_500
