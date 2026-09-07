# ADR-0003: Scenario and financial model persistence ownership

## Status

Accepted

## Context

Domain concepts include FinancialModel (persisted assumptions) and Scenario (overrides). Calculations may run against base models or scenarios, but persistence must have a single owner.

## Decision

- **App Platform** owns persistence of financial models and scenarios (save/commit, retrieval, versioning of stored state).
- **Financial Service** may compute results for a given input set, including ephemeral scenario-style overrides supplied in the request.
- Scenario calculations are initially ephemeral and **MUST NOT** modify a persisted model unless an explicit save/commit occurs in the App Platform.

## Consequences

- This service does not store models or scenarios.
- No requirement to implement scenario APIs until product work requests them; when added, persistence remains out of process.

## References

- `docs/domain-model.md`
- `docs/architecture.md` (State)
