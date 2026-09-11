# Phase 1 structural validation and input independence

## Status

Accepted (Workstream B3)

## Context

After B2 (Operating Surplus), Workstream B3 reviewed whether additional financial
validation was needed. The risk was conflating **calculation validation** (can the
engine use this input?) with **advisory / anomaly detection** (is this farm normal
or efficient?).

B3 decisions (Cedric):

1. Close B3 with documentation of principles; **no new validation rules**.
2. Odd but calculable milk combinations (e.g. zero cows with positive litres per cow)
   remain **ACCEPT** (defined maths, typically €0 milk revenue).
3. **No maximums** on Phase 1 financial drivers.

## Decision

1. **Validation scope:** Phase 1 validates that supplied inputs are structurally and
   logically usable for the named calculation: finite numbers ≥ 0 where applicable;
   required vs optional presence; null / wrong type / unknown field rejected. It does
   **not** judge whether values are realistic, efficient, or commercially good.
2. **Independence:** Every financial input is independent unless a value is genuinely
   required to *run* a named calculation (e.g. the milk trio for `revenue.milk`). Do
   **not** add cross-field rules based on farm correlations (cows vs feed, rent vs acres,
   levies vs milk revenue, etc.).
3. **Limits:** `minimum = 0`, `maximum = none` for Phase 1 annual financial drivers.
   Unusual magnitudes remain acceptable for calculation.
4. **No warning channel in Phase 1:** Soft “unusual but valid” cases are deferred to
   future advisory tooling; they must not become calculation errors.
5. **Finance:** `loan_repayments` validation remains independent of operating costs and
   Operating Surplus (ADR-0007).

## Consequences

- Existing runner / schema behaviour is the Phase 1 contract; B3 does not tighten it.
- Future advisory, benchmarking, KPIs, and anomaly detection must not be implemented by
  silently adding calculation-engine validation maxima or cross-field rejections.
- Characterisation tests may lock independence and “no maxima” without changing rules.

## Related

- `docs/api-contract.md`, `docs/domain-model.md`
- `farm_functions/schemas.py`, `farm_functions/runner.py`
- ADR-0004 (`needs_input`), ADR-0007 (Operating Surplus / finance)
