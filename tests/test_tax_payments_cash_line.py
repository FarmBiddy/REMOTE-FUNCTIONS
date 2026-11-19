"""tax_payments cash line (ADR-0055 §2a): the gross amount paid to Revenue in a month.

Financing outflow next to household drawings: in cash, never on the P&L, and
never projected by cf.forecast (known-only: the Platform sends the months it
expects to pay, from tax.payments).
"""

from farm_functions.runner import run_function


def test_tax_is_a_financing_outflow():
    body = run_function("cf.monthly", {"year": 2026, "month": 11, "milk": 50_000, "tax_payments": 30_000})["result"]
    assert body["financing"]["outflows"]["lines"]["tax_payments"] == 30_000
    assert body["financing"]["outflows"]["total"] == 30_000
    assert body["net_cash_flow"] == 20_000


def test_tax_is_never_on_the_pl():
    result = run_function("pl.monthly", {"year": 2026, "month": 11, "milk_litres": 1, "milk_price": 0.4, "tax_payments": 1})
    assert result["status"] == "error"


def test_forecast_never_guesses_tax():
    history = [{"year": 2025, "month": m, "milk": 1_000, "tax_payments": 900 if m == 11 else 0} for m in range(1, 13)]
    body = run_function("cf.forecast", {
        "history": history,
        "forecast": [{"year": 2026, "month": 10, "tax_payments": 500}, {"year": 2026, "month": 11}],
    })["result"]
    assert [(m["period"]["month"], m["inputs"]["tax_payments"]) for m in body["months"]] == [(10, 500), (11, 0)]
    assert "tax_payments" not in body["run_rate"]
