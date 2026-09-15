"""Deterministic annual input-override simulation (ADR-0011).

Tests simulation behaviour only: override application, validation reuse,
delegation to calculate_annual_pnl. Does not re-prove the full financial suite.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from farm_functions.domain import FinancialInput
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.simulation import (
    SimulationRequest,
    apply_input_overrides,
    simulate_annual_pnl,
)


def _sample_base() -> FinancialInput:
    return FinancialInput.model_validate(load_sample_inputs())


def test_empty_overrides_base_equals_simulated() -> None:
    base = _sample_base()
    result = simulate_annual_pnl(SimulationRequest(base=base, overrides={}))
    assert result.overrides_applied == {}
    assert result.base == result.simulated
    assert result.base.profit.net == 77_000


def test_single_milk_price_override_reference_farm() -> None:
    base = _sample_base()
    result = simulate_annual_pnl(
        SimulationRequest(base=base, overrides={"milk_price": 0.45})
    )
    assert result.overrides_applied == {"milk_price": 0.45}

    assert result.base.revenue.milk == 200_000
    assert result.base.revenue.total == 240_000
    assert result.base.costs.total == 163_000
    assert result.base.profit.net == 77_000
    assert result.base.profit.margin_pct == 32.08
    assert result.base.finance.loan_repayments == 12_000

    assert result.simulated.revenue.milk == 225_000
    assert result.simulated.revenue.total == 265_000
    assert result.simulated.costs.total == 163_000
    assert result.simulated.profit.net == 102_000
    assert result.simulated.profit.margin == 0.3849
    assert result.simulated.profit.margin_pct == 38.49
    assert result.simulated.finance.loan_repayments == 12_000


def test_multiple_overrides_change_only_named_fields() -> None:
    base = _sample_base()
    overrides = {"milk_price": 0.45, "feed": 70_000}
    simulated = apply_input_overrides(base, overrides)

    base_dump = base.model_dump()
    sim_dump = simulated.model_dump()
    changed = {name for name in base_dump if base_dump[name] != sim_dump[name]}
    assert changed == {"milk_price", "feed"}
    assert sim_dump["milk_price"] == 0.45
    assert sim_dump["feed"] == 70_000

    result = simulate_annual_pnl(SimulationRequest(base=base, overrides=overrides))
    assert result.overrides_applied == {"feed": 70_000.0, "milk_price": 0.45}


def test_unknown_override_field_rejected() -> None:
    base = _sample_base()
    with pytest.raises(ValueError, match="unknown simulation override"):
        apply_input_overrides(base, {"not_a_real_field": 1})


def test_negative_override_rejected_by_financial_input() -> None:
    base = _sample_base()
    with pytest.raises(ValidationError):
        apply_input_overrides(base, {"milk_price": -0.10})


def test_null_override_rejected_by_financial_input() -> None:
    base = _sample_base()
    with pytest.raises(ValidationError):
        apply_input_overrides(base, {"feed": None})


def test_wrong_type_override_rejected_by_financial_input() -> None:
    base = _sample_base()
    with pytest.raises(ValidationError):
        apply_input_overrides(base, {"feed": "expensive"})


def test_explicit_zero_override_is_valid() -> None:
    base = _sample_base()
    simulated = apply_input_overrides(base, {"biss": 0})
    assert simulated.biss == 0
    result = simulate_annual_pnl(SimulationRequest(base=base, overrides={"biss": 0}))
    assert result.simulated.revenue.schemes == base.acres + base.other_grants


def test_large_valid_override_accepted() -> None:
    base = _sample_base()
    simulated = apply_input_overrides(base, {"feed": 1_000_000_000})
    assert simulated.feed == 1_000_000_000


def test_base_input_immutable_after_simulation() -> None:
    base = _sample_base()
    before = base.model_dump()
    simulate_annual_pnl(
        SimulationRequest(base=base, overrides={"milk_price": 0.45, "feed": 1})
    )
    assert base.model_dump() == before
    assert base.milk_price == 0.40
    assert base.feed == 80_000


def test_loan_repayments_override_affects_finance_only() -> None:
    base = _sample_base()
    result = simulate_annual_pnl(
        SimulationRequest(base=base, overrides={"loan_repayments": 20_000})
    )
    assert result.simulated.finance.loan_repayments == 20_000
    assert result.base.finance.loan_repayments == 12_000
    assert result.simulated.revenue.total == result.base.revenue.total
    assert result.simulated.costs.total == result.base.costs.total
    assert result.simulated.profit.net == result.base.profit.net
    assert result.simulated.profit.margin == result.base.profit.margin
    assert result.simulated.profit.margin_pct == result.base.profit.margin_pct


def test_simulated_result_reconciles_operating_surplus() -> None:
    base = _sample_base()
    result = simulate_annual_pnl(
        SimulationRequest(base=base, overrides={"milk_price": 0.45, "labour": 50_000})
    )
    sim = result.simulated
    assert sim.profit.net == sim.revenue.total - sim.costs.total
