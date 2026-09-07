# ADR-0004: `needs_input.missing` structured field entries

## Status

Accepted

## Context

The calculation contract returns `needs_input` when required values are absent. Documentation briefly described `missing` as `{field, unit}` objects while the runner, README, and tests used plain string field names. Downstream agents and UIs benefit from explicit units.

## Decision

- Canonical `missing` entries are objects: `{ "field": "<name>", "unit": "<semantic unit>" }`.
- Units are defined in `FIELD_UNITS` in `farm_functions/schemas.py`.
- `provided` remains a sorted list of present field **names** (strings).
- Required missing inputs are **never guessed**.

## Consequences

- Runner, API tests, README, and `docs/api-contract.md` must stay aligned on this shape.
- New input fields must register a unit in `FIELD_UNITS`.

## References

- `docs/api-contract.md`
- `farm_functions/schemas.py`
- `farm_functions/runner.py`
