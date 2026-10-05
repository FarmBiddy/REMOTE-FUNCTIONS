"""kpi.summary (ADR-0028): Dairy KPIs over a set of months.

Hand-checkable quarter, 100 cows:
  Jan 20,000 L × €0.40 = 8,000   feed 6,000  labour 3,000  repayments 1,500
  Feb 40,000 L × €0.40 = 16,000  feed 5,000  labour 3,000  repayments 1,500
  Mar 60,000 L × €0.40 = 24,000  feed 5,000  labour 3,000  repayments 1,500
  Totals: 120,000 L, revenue 48,000, costs 25,000, surplus 23,000, repayments 4,500
  → revenue 40 c/L, costs 20.83 c/L, feed 13.33 c/L, surplus 19.17 c/L
  → 1,200 L/cow, surplus €230/cow, DSCR 23,000 / 4,500 = 5.11
"""

from fastapi.testclient import TestClient

from api.app import app
from farm_functions.runner import run_function

client = TestClient(app)


def _month(month, litres, feed):
    return {
        "year": 2026,
        "month": month,
        "milk_litres": litres,
        "milk_price": 0.40,
        "feed": feed,
        "labour": 3_000,
        "loan_repayments": 1_500,
    }


QUARTER = [_month(3, 60_000, 5_000), _month(1, 20_000, 6_000), _month(2, 40_000, 5_000)]


def _kpis(months=QUARTER, cows=100):
    return run_function("kpi.summary", {"months": months, "milking_cows": cows})


def test_reference_quarter():
    body = _kpis()["result"]
    assert (body["from"]["month"], body["to"]["month"], body["month_count"]) == (1, 3, 3)
    assert body["totals"] == {
        "milk_litres": 120_000,
        "revenue": 48_000,
        "costs": 25_000,
        "surplus": 23_000,
        "loan_repayments": 4_500,
    }
    assert body["per_litre_c"]["revenue"] == 40
    assert body["per_litre_c"]["costs"] == 20.83
    assert body["per_litre_c"]["surplus"] == 19.17
    assert body["per_litre_c"]["cost_lines"]["feed"] == 13.33
    assert body["per_litre_c"]["cost_lines"]["vet"] == 0
    assert body["per_cow"] == {
        "milk_litres": 1_200, "revenue": 480, "costs": 250, "gross_margin": 320, "surplus": 230
    }
    # Variable = feed 16,000 (labour is fixed) → 13.33 c/L; gross margin 32,000.
    assert body["per_litre_c"]["variable_costs"] == 13.33
    assert body["per_litre_c"]["fixed_costs"] == 7.5
    assert body["per_litre_c"]["gross_margin"] == 26.67
    assert body["dscr"] == 5.11


def test_undefined_ratios_are_null():
    no_loans = [{**m, "loan_repayments": 0} for m in QUARTER]
    assert _kpis(no_loans)["result"]["dscr"] is None
    assert _kpis(cows=0)["result"]["per_cow"]["surplus"] is None


def test_loss_gives_negative_surplus_and_dscr():
    body = _kpis([_month(1, 10_000, 9_000)])["result"]
    assert body["totals"]["surplus"] == -8_000
    assert body["dscr"] == round(-8_000 / 1_500, 2)


def test_projected_months_from_forecast_plug_in():
    history = [_month(m, 40_000, 5_000) | {"year": 2025} for m in (10,)] + [_month(9, 30_000, 5_000)]
    projected = run_function(
        "pl.forecast", {"history": history, "forecast": [{"year": 2026, "month": 10}]}
    )["result"]["months"][0]
    body = _kpis([{"year": 2026, "month": 10, **projected["inputs"]}])["result"]
    assert body["totals"]["surplus"] == projected["statement"]["profit"]["net"]


def test_duplicate_month_is_rejected():
    result = _kpis([QUARTER[0], QUARTER[0]])
    assert result["error"]["details"]["reason"] == "duplicate_period"


def test_http_matches_runner():
    payload = {"months": QUARTER, "milking_cows": 100}
    body = client.post("/v1/functions/kpi.summary/run", json=payload).json()
    assert body == run_function("kpi.summary", payload)


def test_optional_solids_hectare_and_debt_blocks():
    """10,000 kg MS, 40 ha, €86,800 debt over the reference quarter (100 cows)."""
    body = run_function(
        "kpi.summary",
        {"months": QUARTER, "milking_cows": 100, "milk_solids_kg": 10_000, "hectares": 40, "debt_balance": 86_800},
    )["result"]
    assert body["per_kg_ms"] == {"revenue": 4.8, "costs": 2.5, "gross_margin": 3.2, "surplus": 2.3}
    assert body["per_hectare"] == {
        "milk_litres": 3_000, "revenue": 1_200, "costs": 625, "gross_margin": 800, "surplus": 575
    }
    assert body["debt"] == {"balance": 86_800, "per_cow": 868, "per_hectare": 2_170}


def test_optional_blocks_are_null_when_not_sent():
    body = _kpis()["result"]
    assert body["per_kg_ms"] is None and body["per_hectare"] is None and body["debt"] is None
    no_ha = run_function(
        "kpi.summary", {"months": QUARTER, "milking_cows": 100, "debt_balance": 1_000}
    )["result"]
    assert no_ha["debt"]["per_hectare"] is None
