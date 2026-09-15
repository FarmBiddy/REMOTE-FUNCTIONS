"""Caller-defined named financial scenarios. No financial formulas.

Packages explicit overrides under a name and delegates execution to B7
simulate_annual_pnl (ADR-0012). B7 remains the override/validation primitive.
"""

from __future__ import annotations

from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, field_validator

from farm_functions.domain import FinancialInput, FinancialResult
from farm_functions.simulation import SimulationRequest, simulate_annual_pnl


class ScenarioDefinition(BaseModel):
    """Named package of explicit FinancialInput overrides. Ephemeral; not persisted."""

    model_config = ConfigDict(extra="forbid")

    name: str
    overrides: dict[str, Any] = {}

    @field_validator("name")
    @classmethod
    def name_must_be_non_blank(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("scenario name must be a non-blank string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("scenario name must be a non-blank string")
        return stripped


class ScenarioResult(BaseModel):
    """One named scenario's simulated Operating Statement."""

    model_config = ConfigDict(extra="forbid")

    name: str
    overrides_applied: dict[str, float]
    result: FinancialResult


class ScenarioBundle(BaseModel):
    """Base statement plus independently calculated scenario results (caller order)."""

    model_config = ConfigDict(extra="forbid")

    base: FinancialResult
    scenarios: list[ScenarioResult]


def run_scenario(base: FinancialInput, scenario: ScenarioDefinition) -> ScenarioResult:
    """Execute one named scenario via B7 simulation. Does not mutate base or scenario."""
    simulation = simulate_annual_pnl(
        SimulationRequest(base=base, overrides=dict(scenario.overrides))
    )
    return ScenarioResult(
        name=scenario.name,
        overrides_applied=simulation.overrides_applied,
        result=simulation.simulated,
    )


def run_scenarios(
    base: FinancialInput,
    scenarios: Sequence[ScenarioDefinition],
) -> ScenarioBundle:
    """Execute each scenario independently from the same base via B7.

    Each scenario calls ``simulate_annual_pnl`` separately (simple, correct Phase 1
    delegation). That may recalculate the base statement once per scenario; the
    published ``ScenarioBundle.base`` is taken from the first simulation when any
    scenarios are present, otherwise from an empty-override simulation. No B7
    redesign for optimisation.
    """
    results: list[ScenarioResult] = []
    base_result: FinancialResult | None = None

    if not scenarios:
        empty = simulate_annual_pnl(SimulationRequest(base=base, overrides={}))
        return ScenarioBundle(base=empty.base, scenarios=[])

    for scenario in scenarios:
        simulation = simulate_annual_pnl(
            SimulationRequest(base=base, overrides=dict(scenario.overrides))
        )
        if base_result is None:
            base_result = simulation.base
        results.append(
            ScenarioResult(
                name=scenario.name,
                overrides_applied=simulation.overrides_applied,
                result=simulation.simulated,
            )
        )

    assert base_result is not None
    return ScenarioBundle(base=base_result, scenarios=results)


__all__ = [
    "ScenarioBundle",
    "ScenarioDefinition",
    "ScenarioResult",
    "run_scenario",
    "run_scenarios",
]
