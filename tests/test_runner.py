from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import list_functions
from farm_functions.runner import run_function
from farm_functions.version import ENGINE_VERSION


def test_needs_input_when_milk_price_missing():
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000},
    )
    assert result["status"] == "needs_input"
    assert result["missing"] == [{"field": "milk_price", "unit": "EUR/litre"}]
    assert result["provided"] == ["litres_per_cow", "milking_cows"]


def test_unknown_function():
    result = run_function("montecarlo.run", {})
    assert result["status"] == "error"
    assert result["error"]["code"] == "unknown_calculation"
    assert "Unknown function" in result["message"]


def test_milk_revenue_ok():
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0.40},
    )
    assert result == {
        "status": "ok",
        "function": "revenue.milk",
        "result": {"amount": 200000.0, "currency": "EUR"},
        "meta": {"engine_version": ENGINE_VERSION},
    }


def test_profit_margin_ok():
    result = run_function("profit.margin", {"revenue": 240_000, "costs": 163_000})
    assert result["status"] == "ok"
    assert result["result"]["margin"] == 0.3208
    assert result["result"]["margin_pct"] == 32.08
    assert result["result"]["profit"] == 77_000


def test_sample_farm_pl_summary():
    result = run_function("pl.summary", load_sample_inputs())
    assert result["status"] == "ok"
    payload = result["result"]
    assert payload["revenue"]["milk"] == 200_000
    assert payload["revenue"]["total"] == 240_000
    assert payload["costs"]["total"] == 163_000
    assert payload["profit"]["net"] == 77_000
    assert payload["profit"]["margin_pct"] == 32.08
    assert payload["finance"]["loan_repayments"] == 12_000
    assert "loan_repayments" not in payload["costs"]["lines"]


def test_discovery_lists_core_functions_only():
    keys = {item["key"] for item in list_functions()}
    assert keys == {
        "cf.monthly",
        "cf.months",
        "loan.schedule",
        "kpi.summary",
        "risk.sensitivity",
        "risk.tornado",
        "decision.partial_budget",
        "decision.investment",
        "pl.compare",
        "cf.compare",
        "debt.capacity",
        "assets.schedule",
        "pl.net",
        "milk.quality",
        "bs.summary",
        "report.bank",
        "report.advisor",
        "report.accountant",
        "plan.projection",
        "pl.forecast",
        "cf.forecast",
        "costs.total",
        "pl.monthly",
        "pl.months",
        "pl.summary",
        "profit.margin",
        "profit.net",
        "revenue.milk",
        "revenue.other",
        "revenue.schemes",
        "revenue.total",
    }


def test_nested_missing_fields_ask_with_paths():
    """ADR-0027: Biddy can ask for each missing nested value by its path."""
    loan = {"annual_rate": 0.04, "remaining_months": 12, "year": 2026, "month": 10}
    result = run_function("loan.schedule", {"loans": [{**loan, "balance": 1}, loan]})
    assert result["status"] == "needs_input"
    assert result["missing"] == [{"field": "balance", "unit": "EUR", "path": "loans[1].balance"}]
    assert result["provided"] == ["loans"]

    cash = run_function("cf.months", {"opening_cash": 0, "months": [{"year": 2026}]})
    assert cash["missing"] == [{"field": "month", "unit": "month", "path": "months[0].month"}]
