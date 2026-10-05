# Remove in-process annual simulation and named scenarios

## Status

Accepted (insights). Supersedes ADR-0011 and ADR-0012.

## Context

`simulate_annual_pnl` (B7) and `run_scenario` / `run_scenarios` (B8) applied
input overrides to the annual `FinancialInput`, in-process only. No HTTP route
or Platform used them. `risk.sensitivity` now covers what-ifs over HTTP on the
monthly model (price, volume, herd, per-line shocks, investments, break-evens).
Keeping both meant two scenario mechanisms to maintain and explain.

## Decision

Delete `farm_functions/simulation.py`, `farm_functions/scenarios.py`, their
tests and package exports. What-if analysis is `risk.sensitivity` only.

## Consequences

- In-process callers of the removed symbols must call `risk.sensitivity`
  (HTTP or `run_function`) instead. None were known in this repo or the Platform.
- Scenario persistence stays Platform-owned (ADR-0003).

## Related

ADR-0003, ADR-0011, ADR-0012, ADR-0029
