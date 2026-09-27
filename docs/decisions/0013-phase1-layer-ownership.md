# Phase 1 layer ownership (Dairy cost catalogue; land leasing)

## Status

Accepted (L1 classification decisions D1–D2)

## Context

The Financial Engine will progressively separate Dairy, Agriculture, and Core
responsibilities. L0 fixed the Dairy Phase 1 field contract. L1 classified
ownership without moving code. Two product decisions were required before L2:

1. Who owns the Phase 1 named operating-cost catalogue (`OPERATING_COST_CATEGORIES`
   / farmer-entered cost lines on `FinancialInput`).
2. How to classify `land_leasing_income` (lease owned land out) while it remains
   on the current Dairy contract.

## Decision

1. **D1 — Phase 1 cost catalogue is Dairy-owned.** Farmer-entered operating-cost
   lines on the Phase 1 `FinancialInput` / `pl.summary` contract are owned by the
   **Dairy** vertical for now. An Agriculture shared-cost catalogue is deferred
   until multi-enterprise or shared-farm work needs it. Core must not own these
   field names; Core only consumes monetary amounts.
2. **D2 — `land_leasing_income` is Agriculture semantics on the Dairy contract.**
   Conceptually the field is an **Agriculture** / farm land concept (income from
   leasing owned land out). It remains an accepted optional field on the current
   Dairy Phase 1 input contract and continues to contribute to `revenue.other`.
   It is not netted against `rent_lease` (rent/lease in).

## Consequences

- L2 must not invent parallel `agriculture.feed` / `core.electricity` inputs for
  the same farmer values.
- Empty Agriculture packages are not required solely to “own” cost lines yet.
- Future Agri module work may absorb `land_leasing_income` (and later schemes /
  shared costs) without changing the farmer-facing Dairy field name in Phase 1
  unless a separate contract change is approved.
- Dependency intent remains: Dairy → Agriculture → Core, with Dairy → Core
  allowed; Core must not depend on Dairy or Agriculture.

## Related

- L0 Dairy contract (`land_leasing_income`, `water`, cost catalogue)
- ADR-0007 (Operating Surplus and operating-cost catalogue)
- `docs/domain-model.md`, `docs/architecture.md`
