"""pl.forecast / cf.forecast (ADR-0026): seasonal base × run-rate, known values win.

Hand-checkable farm: 2025 every month 40,000 L at €0.40, feed €5,000.
2026 Jan–Sep 42,000 L (+5%) at €0.42, feed €5,500 (+10%).
→ Oct-2026: 40,000 × 1.05 = 42,000 L at €0.42 = €17,640; feed 5,000 × 1.1 = €5,500.
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.core.forecast import latest_non_zero, run_rate
from farm_functions.runner import run_function

client = TestClient(app)

PL_HISTORY = [
    {"year": 2025, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 5_000}
    for m in range(1, 13)
] + [
    {"year": 2026, "month": m, "milk_litres": 42_000, "milk_price": 0.42, "feed": 5_500}
    for m in range(1, 10)
]
OCT_TO_DEC = [{"year": 2026, "month": m} for m in (10, 11, 12)]


def _pl(forecast=OCT_TO_DEC, history=PL_HISTORY):
    return run_function("pl.forecast", {"history": history, "forecast": forecast})


def test_seasonal_base_scaled_by_run_rate():
    body = _pl()["result"]
    assert body["as_of"] == {"kind": "month", "year": 2026, "month": 9}
    assert body["run_rate"]["milk_litres"] == 1.05
    assert body["run_rate"]["feed"] == 1.1
    oct_ = body["months"][0]
    assert oct_["inputs"]["milk_litres"] == 42_000
    assert oct_["inputs"]["feed"] == 5_500
    assert oct_["statement"]["revenue"]["milk"] == 17_640
    assert oct_["statement"]["profit"]["net"] == 12_140


def test_known_values_override_projection():
    body = _pl([{"year": 2026, "month": 10, "milk_price": 0.45, "biss": 6_000}])["result"]
    oct_ = body["months"][0]
    assert oct_["statement"]["revenue"]["milk"] == 18_900  # 42,000 × 0.45
    assert oct_["inputs"]["biss"] == 6_000


def test_loan_repayments_not_projected_from_history():
    history = [dict(PL_HISTORY[9], loan_repayments=1_500), *PL_HISTORY[12:]]
    oct_ = _pl([{"year": 2026, "month": 10}], history)["result"]["months"][0]
    assert oct_["inputs"]["loan_repayments"] == 0


def test_price_carries_latest_non_zero_actual():
    assert latest_non_zero({1: {"p": 0.4}, 2: {"p": 0.0}}, "p") == 0.4
    assert run_rate(5, 0) == 1.0


def test_errors_have_reasons():
    overlap = _pl([{"year": 2026, "month": 9}])
    assert overlap["error"]["details"]["reason"] == "forecast_overlaps_history"
    no_prior = _pl([{"year": 2026, "month": 10}], PL_HISTORY[12:])
    assert no_prior["error"]["details"]["reason"] == "missing_prior_year_month"
    dup = _pl([{"year": 2026, "month": 10}, {"year": 2026, "month": 10}])
    assert dup["error"]["details"]["reason"] == "duplicate_period"


CF_HISTORY = [
    {"year": 2025, "month": 10, "milk": 16_000, "feed": 5_000, "machinery_equipment_payments": 30_000},
    {"year": 2026, "month": 9, "milk": 15_000, "feed": 4_000},
]


def test_cash_one_offs_not_projected_and_loan_rows_plug_in():
    loan = run_function(
        "loan.schedule",
        {"loans": [{"balance": 10_000, "annual_rate": 0.12, "remaining_months": 12, "year": 2026, "month": 10}]},
    )["result"]["months"][0]
    body = run_function(
        "cf.forecast",
        {
            "history": CF_HISTORY,
            "forecast": [
                {
                    "year": 2026,
                    "month": 10,
                    "interest_paid": loan["interest"],
                    "loan_principal_repayments": loan["principal"],
                }
            ],
        },
    )["result"]
    oct_ = body["months"][0]
    assert oct_["inputs"]["machinery_equipment_payments"] == 0
    assert oct_["cash_flow"]["financing"]["outflows"]["total"] == loan["payment"]
    assert oct_["cash_flow"]["operating"]["net"] == 11_000


def test_projected_inputs_roll_forward_with_actuals():
    """Platform sends actual Sep + projected Oct to cf.months for the balance."""
    projected = run_function(
        "cf.forecast", {"history": CF_HISTORY, "forecast": [{"year": 2026, "month": 10}]}
    )["result"]["months"][0]
    rolled = run_function(
        "cf.months",
        {
            "opening_cash": 1_000,
            "months": [CF_HISTORY[1], {"year": 2026, "month": 10, **projected["inputs"]}],
        },
    )["result"]
    assert rolled["closing_cash"] == 1_000 + 11_000 + 11_000


def test_http_matches_runner():
    payload = {"history": PL_HISTORY, "forecast": OCT_TO_DEC}
    body = client.post("/v1/functions/pl.forecast/run", json=payload).json()
    assert body == run_function("pl.forecast", payload)
