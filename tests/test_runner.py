from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import list_functions
from farm_functions.runner import run_function


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
    }


def test_profit_margin_ok():
    result = run_function("profit.margin", {"revenue": 240_000, "costs": 175_000})
    assert result["status"] == "ok"
    assert result["result"]["margin"] == 0.2708
    assert result["result"]["margin_pct"] == 27.08
    assert result["result"]["profit"] == 65_000


def test_sample_farm_pl_summary():
    result = run_function("pl.summary", load_sample_inputs())
    assert result["status"] == "ok"
    payload = result["result"]
    assert payload["revenue"]["milk"] == 200_000
    assert payload["revenue"]["total"] == 240_000
    assert payload["costs"]["total"] == 175_000
    assert payload["profit"]["net"] == 65_000
    assert payload["profit"]["margin_pct"] == 27.08


def test_discovery_lists_core_functions_only():
    keys = {item["key"] for item in list_functions()}
    assert keys == {
        "costs.total",
        "pl.summary",
        "profit.margin",
        "profit.net",
        "revenue.milk",
        "revenue.other",
        "revenue.schemes",
        "revenue.total",
    }
