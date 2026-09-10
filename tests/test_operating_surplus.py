"""Phase 1 Operating Surplus behaviour (ADR-0007)."""

from __future__ import annotations

from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES
from farm_functions.calcs.summary import pl_summary
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.runner import run_function

NEW_OPERATING_COSTS = (
    "repairs_maintenance",
    "rent_lease",
    "professional_fees",
    "levies",
    "other_operating_costs",
)


def _base_operating_drivers() -> dict:
    data = load_sample_inputs()
    data["loan_repayments"] = 0
    return data


def test_operating_surplus_equals_income_minus_operating_costs() -> None:
    result = run_function("pl.summary", load_sample_inputs())["result"]
    assert result["profit"]["net"] == result["revenue"]["total"] - result["costs"]["total"]
    assert result["profit"]["net"] == 77_000
    assert result["costs"]["total"] == 163_000


def test_loan_repayments_do_not_change_operating_surplus() -> None:
    base = _base_operating_drivers()
    zero = pl_summary(**{**base, "loan_repayments": 0})
    twelve = pl_summary(**{**base, "loan_repayments": 12_000})
    twenty = pl_summary(**{**base, "loan_repayments": 20_000})

    assert zero["profit"]["net"] == twelve["profit"]["net"] == twenty["profit"]["net"]
    assert zero["costs"]["total"] == twelve["costs"]["total"] == twenty["costs"]["total"]
    assert zero["finance"]["loan_repayments"] == 0
    assert twelve["finance"]["loan_repayments"] == 12_000
    assert twenty["finance"]["loan_repayments"] == 20_000


def test_costs_total_excludes_loan_repayments() -> None:
    operating = {
        "feed": 80_000,
        "fertiliser": 15_000,
        "vet": 5_000,
        "contractor": 10_000,
        "labour": 40_000,
        "insurance": 4_000,
        "fuel": 6_000,
        "electricity": 3_000,
    }
    result = run_function("costs.total", operating)
    assert result["status"] == "ok"
    assert result["result"]["amount"] == 163_000

    rejected = run_function("costs.total", {**operating, "loan_repayments": 12_000})
    assert rejected["status"] == "error"
    assert rejected["error"]["code"] == "unknown_field"
    assert rejected["error"]["field"] == "loan_repayments"


def test_each_new_operating_cost_reduces_surplus() -> None:
    base = pl_summary(**load_sample_inputs())
    base_surplus = base["profit"]["net"]
    for name in NEW_OPERATING_COSTS:
        drivers = {**load_sample_inputs(), name: 1_000}
        updated = pl_summary(**drivers)
        assert updated["costs"]["lines"][name] == 1_000
        assert updated["costs"]["total"] == base["costs"]["total"] + 1_000
        assert updated["profit"]["net"] == base_surplus - 1_000


def test_operating_cost_catalogue_keys_match_pl_summary_lines() -> None:
    result = pl_summary(**load_sample_inputs())
    assert list(result["costs"]["lines"]) == list(OPERATING_COST_CATEGORIES)
    assert "loan_repayments" not in result["costs"]["lines"]
    for name in NEW_OPERATING_COSTS:
        assert name in OPERATING_COST_CATEGORIES


def test_omitted_optional_operating_costs_default_to_zero() -> None:
    result = run_function(
        "pl.summary",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0.40},
    )["result"]
    for name in OPERATING_COST_CATEGORIES:
        assert result["costs"]["lines"][name] == 0
    assert result["costs"]["total"] == 0
    assert result["finance"]["loan_repayments"] == 0
    assert result["profit"]["net"] == 200_000
