"""Caller-defined named scenarios via B7 simulation (ADR-0012).

Tests scenario packaging/orchestration only — not the full financial suite.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from farm_functions.domain import FinancialInput
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.scenarios import (
    ScenarioDefinition,
    run_scenario,
    run_scenarios,
)
from farm_functions.simulation import SimulationRequest, simulate_annual_pnl


def _sample_base() -> FinancialInput:
    return FinancialInput.model_validate(load_sample_inputs())


def test_named_scenario_matches_b7_simulated_result() -> None:
    base = _sample_base()
    overrides = {"milk_price": 0.35}
    scenario = ScenarioDefinition(name="Milk Price Downside", overrides=overrides)
    via_scenario = run_scenario(base, scenario)
    via_b7 = simulate_annual_pnl(SimulationRequest(base=base, overrides=overrides))
    assert via_scenario.result == via_b7.simulated
    assert via_scenario.overrides_applied == via_b7.overrides_applied
    assert via_scenario.name == "Milk Price Downside"
    assert via_scenario.result.revenue.milk == 175_000
    assert via_scenario.result.revenue.total == 215_000
    assert via_scenario.result.costs.total == 163_000
    assert via_scenario.result.profit.net == 52_000
    assert via_scenario.result.finance.loan_repayments == 12_000


def test_higher_milk_price_scenario_reference_numbers() -> None:
    base = _sample_base()
    result = run_scenario(
        base, ScenarioDefinition(name="Higher Milk Price", overrides={"milk_price": 0.45})
    )
    assert result.result.revenue.milk == 225_000
    assert result.result.revenue.total == 265_000
    assert result.result.costs.total == 163_000
    assert result.result.profit.net == 102_000
    assert result.result.profit.margin_pct == 38.49


def test_multiple_overrides_in_one_scenario() -> None:
    base = _sample_base()
    overrides = {"milk_price": 0.35, "feed": 70_000}
    scenario = ScenarioDefinition(name="Downside Package", overrides=overrides)
    result = run_scenario(base, scenario)
    via_b7 = simulate_annual_pnl(SimulationRequest(base=base, overrides=overrides))
    assert result.result == via_b7.simulated
    assert result.overrides_applied == {"feed": 70_000.0, "milk_price": 0.35}


def test_empty_overrides_equals_base_statement() -> None:
    base = _sample_base()
    bundle = run_scenarios(
        base, [ScenarioDefinition(name="Current Position", overrides={})]
    )
    assert len(bundle.scenarios) == 1
    assert bundle.scenarios[0].result == bundle.base
    assert bundle.base.profit.net == 77_000


def test_blank_and_whitespace_names_rejected() -> None:
    with pytest.raises(ValidationError):
        ScenarioDefinition(name="")
    with pytest.raises(ValidationError):
        ScenarioDefinition(name="   ")


def test_invalid_financial_override_surfaces_via_b7() -> None:
    base = _sample_base()
    with pytest.raises(ValidationError):
        run_scenario(
            base, ScenarioDefinition(name="Bad Price", overrides={"milk_price": -0.10})
        )
    with pytest.raises(ValueError, match="unknown simulation override"):
        run_scenario(
            base, ScenarioDefinition(name="Unknown", overrides={"not_a_field": 1})
        )


def test_base_immutable_after_scenarios() -> None:
    base = _sample_base()
    before = base.model_dump()
    run_scenarios(
        base,
        [
            ScenarioDefinition(name="A", overrides={"milk_price": 0.35}),
            ScenarioDefinition(name="B", overrides={"feed": 70_000}),
        ],
    )
    assert base.model_dump() == before


def test_scenario_definition_immutable_after_run() -> None:
    base = _sample_base()
    overrides = {"milk_price": 0.35, "feed": 70_000}
    scenario = ScenarioDefinition(name="Pkg", overrides=overrides)
    overrides_before = copy.deepcopy(scenario.overrides)
    name_before = scenario.name
    run_scenario(base, scenario)
    assert scenario.name == name_before
    assert scenario.overrides == overrides_before
    assert overrides == {"milk_price": 0.35, "feed": 70_000}


def test_scenarios_independent_from_same_base() -> None:
    base = _sample_base()
    assert base.milk_price == 0.40
    assert base.feed == 80_000
    bundle = run_scenarios(
        base,
        [
            ScenarioDefinition(name="Milk Downside", overrides={"milk_price": 0.35}),
            ScenarioDefinition(name="Higher Feed", overrides={"feed": 70_000}),
        ],
    )
    milk_case, feed_case = bundle.scenarios
    assert milk_case.result.revenue.milk == 175_000
    assert milk_case.result.costs.lines.feed == 80_000
    assert feed_case.result.revenue.milk == 200_000
    assert feed_case.result.costs.lines.feed == 70_000
    assert feed_case.result.revenue.total == bundle.base.revenue.total


def test_caller_order_preserved() -> None:
    base = _sample_base()
    bundle = run_scenarios(
        base,
        [
            ScenarioDefinition(name="C", overrides={"milk_price": 0.45}),
            ScenarioDefinition(name="A", overrides={"milk_price": 0.35}),
            ScenarioDefinition(name="B", overrides={"feed": 1}),
        ],
    )
    assert [item.name for item in bundle.scenarios] == ["C", "A", "B"]


def test_duplicate_names_allowed_and_positional() -> None:
    base = _sample_base()
    bundle = run_scenarios(
        base,
        [
            ScenarioDefinition(name="Downside", overrides={"milk_price": 0.35}),
            ScenarioDefinition(name="Downside", overrides={"milk_price": 0.45}),
        ],
    )
    assert [item.name for item in bundle.scenarios] == ["Downside", "Downside"]
    assert bundle.scenarios[0].result.profit.net == 52_000
    assert bundle.scenarios[1].result.profit.net == 102_000


def test_loan_only_scenario_changes_finance_not_surplus() -> None:
    base = _sample_base()
    bundle = run_scenarios(
        base,
        [ScenarioDefinition(name="More Debt Service", overrides={"loan_repayments": 20_000})],
    )
    scenario = bundle.scenarios[0]
    assert scenario.result.finance.loan_repayments == 20_000
    assert scenario.result.revenue.total == bundle.base.revenue.total
    assert scenario.result.costs.total == bundle.base.costs.total
    assert scenario.result.profit.net == bundle.base.profit.net
    assert scenario.result.profit.margin == bundle.base.profit.margin
    assert scenario.result.profit.margin_pct == bundle.base.profit.margin_pct


def test_scenario_deterministic() -> None:
    base = _sample_base()
    scenario = ScenarioDefinition(name="Milk Price Downside", overrides={"milk_price": 0.35})
    first = run_scenario(base, scenario)
    second = run_scenario(base, scenario)
    assert first == second
