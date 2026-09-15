"""Pure farm cost and revenue calculations for agent/server use."""

from farm_functions.domain import (
    FinancialInput,
    FinancialModel,
    FinancialResult,
    calculate_annual_pnl,
)
from farm_functions.provenance import (
    CalculationProvenance,
    explain_annual_pnl,
)
from farm_functions.registry import list_functions
from farm_functions.runner import run_function
from farm_functions.schemas import list_input_metadata
from farm_functions.simulation import (
    SimulationRequest,
    SimulationResult,
    simulate_annual_pnl,
)
from farm_functions.scenarios import (
    ScenarioBundle,
    ScenarioDefinition,
    ScenarioResult,
    run_scenario,
    run_scenarios,
)

__all__ = [
    "CalculationProvenance",
    "FinancialInput",
    "FinancialModel",
    "FinancialResult",
    "ScenarioBundle",
    "ScenarioDefinition",
    "ScenarioResult",
    "SimulationRequest",
    "SimulationResult",
    "calculate_annual_pnl",
    "explain_annual_pnl",
    "list_functions",
    "list_input_metadata",
    "run_function",
    "run_scenario",
    "run_scenarios",
    "simulate_annual_pnl",
]
