# Dairy boundary consolidation (post-L4 gate)

## Status

Accepted (Dairy Boundary Consolidation gate)

## Context

L4 extracted Dairy specialisation (ADR-0015). Before adding further
product capability or a second enterprise specialisation, ownership inside
Dairy needed a consolidation gate: confirm Dairy is a composition /
specialisation layer, not a second home for Core or Agriculture maths.

## Decision

1. **No ownership moves in this gate.** Audit found Dairy’s modules correctly
   placed relative to ADR-0013 / ADR-0014 / ADR-0015. Moving the Phase 1
   operating-cost catalogue or `land_leasing_income` composition out of Dairy
   would contradict those ADRs and is deferred until multi-enterprise demand.
2. **Canonical formula homes remain:**
   - Core: `sum_amounts`, Operating Surplus / margins, publish rounding
   - Agriculture: `scheme_revenue`
   - Dairy: `milk_revenue`, `other_revenue` / `total_revenue`, cost catalogue /
     `total_costs`, `pl_summary`
   - `calcs.*` and `farm_functions.rounding`: compatibility re-exports only
3. **Dairy Operating Statement** composes Agriculture schemes and Core surplus /
   rounding / aggregation; it must not reimplement those formula bodies.
4. **Layer meanings** (also reflected in `docs/architecture.md`):
   - Core — financial mathematics independent of farming
   - Agriculture — concepts common across agricultural enterprises
   - Dairy — dairy-specific financial specialisation
   - Application/API — orchestration and external contracts

## Consequences

- Dependency direction stays protected by `tests/test_layer_import_boundaries.py`.
- Next architectural work should be the orchestration / composition service seam
  (L5), not Beef/Sheep/Tillage extraction.
- Public calculation IDs, HTTP contracts, and the €240k / €163k / €77k reference
  remain unchanged by this gate.

## Related

- ADR-0013, ADR-0014, ADR-0015
- `docs/architecture.md`
- `tests/test_layer_import_boundaries.py`
