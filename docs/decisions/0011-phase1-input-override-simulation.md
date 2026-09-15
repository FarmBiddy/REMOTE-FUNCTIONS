# Phase 1 annual input-override simulation

## Status

Accepted (Workstream B7)

## Context

Callers need to ask “what if one or more drivers change?” without inventing a second
financial engine, named scenarios, forecasts, or automatic farm correlations. ADR-0003
allows ephemeral override-style computation in this service; persistence of scenarios
remains on the App Platform.

## Decision

1. **Simulation changes inputs, never formulas.** Simulation is:
   `base FinancialInput` + explicit overrides → new validated `FinancialInput` →
   existing `calculate_annual_pnl` for both base and simulated results.
2. **Module boundary.** Simulation lives in `farm_functions/simulation.py` on top of
   domain types. It must not reimplement milk/costs/surplus maths.
3. **Validation.** Override field names must be `FinancialInput` fields. Unknown keys
   are rejected. Merged values are validated by `FinancialInput` (B3 semantics). No
   separate simulation validation rules.
4. **Independence.** Only explicitly named override fields change; no cross-field
   inference (ADR-0008).
5. **Deterministic and stateless.** Same base + same overrides → same result. No saved
   simulations, IDs, or history.
6. **Result shape.** Return `base` `FinancialResult`, `simulated` `FinancialResult`, and
   `overrides_applied`. No engine-side delta/comparison framework or
   favourable/unfavourable labels.
7. **Not scenarios.** B7 is not Base/Best/Worst, named packages, sensitivity ranges,
   forecasting, probabilities, or Monte Carlo. A later B8 may reuse this primitive for
   named assumption packages.
8. **HTTP.** Phase 1 simulation is in-process only (no simulation HTTP endpoint in B7).
9. **Provenance.** Use existing `explain_annual_pnl` on the simulated input; do not add
   simulation-specific provenance (ADR-0010).

## Consequences

- Platform/agent can compare base vs simulated Operating Statements without guessing.
- Finance-only overrides still leave Operating Surplus unchanged (ADR-0007).
- Scenario libraries and sensitivity grids remain out of this service’s B7 scope.

## Related

- `docs/domain-model.md`, `docs/api-contract.md`
- ADR-0003, ADR-0007, ADR-0008, ADR-0009, ADR-0010
- `farm_functions/simulation.py`, `farm_functions/domain.py`
