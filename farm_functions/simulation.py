"""Deterministic annual input-override simulation. No financial formulas.

Applies explicit overrides to a copy of FinancialInput, then delegates both the
base and simulated runs to calculate_annual_pnl (ADR-0011).
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    FinancialResult,
    calculate_annual_pnl,
)


class SimulationRequest(BaseModel):
    """In-process simulation: base drivers plus explicit field overrides."""

    model_config = ConfigDict(extra="forbid")

    base: FinancialInput
    overrides: dict[str, Any] = {}


class SimulationResult(BaseModel):
    """Base and simulated Operating Statements plus the overrides that were applied."""

    model_config = ConfigDict(extra="forbid")

    base: FinancialResult
    simulated: FinancialResult
    overrides_applied: dict[str, float]


def apply_input_overrides(
    base: FinancialInput,
    overrides: Mapping[str, Any],
) -> FinancialInput:
    """Return a new FinancialInput = base with exactly the named fields replaced.

    Does not mutate ``base``. Unknown override keys are rejected before merge.
    Merged values are validated by FinancialInput (B3 semantics).
    """
    known = FinancialInput.model_fields
    unknown = sorted(name for name in overrides if name not in known)
    if unknown:
        raise ValueError(
            "unknown simulation override field(s): " + ", ".join(unknown)
        )

    payload = base.model_dump()
    for name, value in overrides.items():
        payload[name] = value
    return FinancialInput.model_validate(payload)


def simulate_annual_pnl(request: SimulationRequest) -> SimulationResult:
    """Rerun the canonical annual model for base and for base+overrides.

    Contains no revenue/cost/surplus formulas — only input merge + calculate_annual_pnl.
    """
    simulated_input = apply_input_overrides(request.base, request.overrides)
    base_result = calculate_annual_pnl(FinancialModel(inputs=request.base))
    simulated_result = calculate_annual_pnl(FinancialModel(inputs=simulated_input))
    simulated_dump = simulated_input.model_dump()
    overrides_applied = {
        name: float(simulated_dump[name]) for name in sorted(request.overrides)
    }
    return SimulationResult(
        base=base_result,
        simulated=simulated_result,
        overrides_applied=overrides_applied,
    )


__all__ = [
    "SimulationRequest",
    "SimulationResult",
    "apply_input_overrides",
    "simulate_annual_pnl",
]
