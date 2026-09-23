"""Characterise Phase 1 validation independence (ADR-0008).

These tests lock product decisions: structural validation only, no maxima,
independent inputs, odd-but-calculable milk combos remain ok. They do not add rules.
"""

from __future__ import annotations

from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES
from farm_functions.runner import run_function
from farm_functions.schemas import INPUT_FIELD_METADATA


PHASE1_FINANCIAL_FIELDS = (
    "milking_cows",
    "litres_per_cow",
    "milk_price",
    "biss",
    "acres",
    "other_grants",
    "cattle_sales",
    "lamb_sales",
    "wool",
    "other",
    *OPERATING_COST_CATEGORIES,
    "loan_repayments",
)


def test_phase1_financial_fields_have_no_maximum() -> None:
    by_name = {item.name: item for item in INPUT_FIELD_METADATA}
    for name in PHASE1_FINANCIAL_FIELDS:
        assert by_name[name].minimum == 0
        assert by_name[name].maximum is None


def test_zero_cows_with_positive_litres_is_ok_zero_milk() -> None:
    result = run_function(
        "pl.summary",
        {
            "milking_cows": 0,
            "litres_per_cow": 6000,
            "milk_price": 0.40,
        },
    )
    assert result["status"] == "ok"
    assert result["result"]["revenue"]["milk"] == 0.0
    assert result["result"]["profit"]["net"] == 0.0


def test_zero_milk_price_is_ok() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0},
    )
    assert result["status"] == "ok"
    assert result["result"]["amount"] == 0.0


def test_large_unusual_magnitudes_still_calculate() -> None:
    result = run_function(
        "pl.summary",
        {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_price": 5.0,
            "contractor": 1_000_000,
            "cattle_sales": 2_000_000,
        },
    )
    assert result["status"] == "ok"
    assert result["result"]["revenue"]["milk"] == 2_500_000.0
    assert result["result"]["costs"]["total"] == 1_000_000.0
    assert result["result"]["profit"]["net"] == 3_500_000.0


def test_each_operating_cost_may_be_zero_independently() -> None:
    for name in OPERATING_COST_CATEGORIES:
        payload = {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_price": 0.40,
            name: 0,
        }
        result = run_function("pl.summary", payload)
        assert result["status"] == "ok", name
        assert result["result"]["costs"]["lines"][name] == 0.0


def test_loan_repayments_do_not_join_costs_total_validation() -> None:
    """Finance stays off costs.total; presence there is unknown_field, not a cross-rule."""
    rejected = run_function(
        "costs.total",
        {"feed": 1000, "loan_repayments": 12_000},
    )
    assert rejected["status"] == "error"
    assert rejected["error"]["code"] == "unknown_field"
    assert rejected["error"]["field"] == "loan_repayments"

    accepted = run_function(
        "pl.summary",
        {
            "milking_cows": 100,
            "litres_per_cow": 5000,
            "milk_price": 0.40,
            "loan_repayments": 12_000,
        },
    )
    assert accepted["status"] == "ok"
    assert accepted["result"]["finance"]["loan_repayments"] == 12_000
    assert accepted["result"]["costs"]["total"] == 0.0
    assert accepted["result"]["profit"]["net"] == 200_000.0
