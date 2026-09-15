# Phase 1 caller-defined named financial scenarios

## Status

Accepted (Workstream B8)

## Context

B7 provides deterministic input-override simulation. Callers also need to package
assumptions under a meaningful name and optionally run several such packages against
the same farm without inventing a second calculator, forecasts, ranking, or persistence
in this service. ADR-0003 already assigns scenario persistence to the App Platform.

## Decision

1. **Scenarios are named override packages.** A `ScenarioDefinition` is a non-blank
   `name` plus explicit `overrides`. It contains no financial formulas.
2. **B7 remains the execution primitive.** Scenario execution builds
   `SimulationRequest(base, overrides)` and calls `simulate_annual_pnl`. Financial
   field validation stays with B7 / `FinancialInput`.
3. **Module boundary.** Scenarios live in `farm_functions/scenarios.py` on top of
   simulation; they must not reimplement merge or revenue/cost/surplus maths.
4. **Independence.** Each scenario applies overrides to the original base only — never
   to another scenario’s result.
5. **Results.** `ScenarioResult` carries `name`, `overrides_applied`, and simulated
   `FinancialResult`. `ScenarioBundle` carries one `base` `FinancialResult` plus
   scenario results in caller order. No engine deltas, ranking, or judgement labels.
6. **Names.** Blank/whitespace-only names are invalid. Duplicate names are allowed
   (positional). Strings such as Base/Best/Worst are ordinary names with no special
   engine semantics.
7. **Empty overrides** are valid (named base-equivalent case via B7).
8. **Deterministic and ephemeral.** Same base + same definition → same result. No
   saved scenarios, IDs, history, or ownership here.
9. **Not forecasting / sensitivity.** Caller supplies assumptions; the engine does not
   generate ranges, probabilities, or predictions.
10. **HTTP.** Phase 1 scenarios are in-process only (no scenario HTTP endpoint in B8).
11. **Provenance.** Use existing `explain_annual_pnl` on the simulated input; no
    scenario-specific provenance type.

## Consequences

- Platform can present named cases (including user-chosen “Base/Best/Worst” labels)
  without the engine interpreting them.
- Multi-scenario runs may recalculate the base once per B7 call; Phase 1 prefers
  simple correct delegation over optimising B7.
- Persistence and scenario libraries remain App Platform concerns (ADR-0003).

## Related

- `docs/domain-model.md`, `docs/api-contract.md`
- ADR-0003, ADR-0011
- `farm_functions/scenarios.py`, `farm_functions/simulation.py`
