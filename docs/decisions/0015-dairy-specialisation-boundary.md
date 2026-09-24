# Dairy specialisation package boundary (L4)

## Status

Accepted (L4 Dairy extraction)

## Context

L2/L3 established Core money primitives and Agriculture `scheme_revenue`
(ADR-0014). Milk revenue, the Phase 1 operating-cost catalogue, other-income
composition, and `pl_summary` still lived under `farm_functions.calcs`, which
hid Dairy ownership behind a generic package name.

## Decision

1. **Dairy (`farm_functions.dairy`)** owns Phase 1 Dairy financial specialisation:
   `milk_revenue`, `other_revenue` / `total_revenue` composition, the operating-cost
   catalogue (`OPERATING_COST_CATEGORIES` / `total_costs`), and canonical annual
   Operating Statement composition (`pl_summary`).
2. **`calcs.revenue` / `calcs.costs` / `calcs.summary`** become thin re-exports so
   public calculation IDs, registry handlers, and existing imports stay stable.
   There is one implementation of each formula.
3. **`FinancialInput`** remains the stable public type name; conceptually it is the
   Phase 1 Dairy input contract. Do not introduce a parallel `DairyFinancialInput`
   with duplicate fields.
4. **Schemes stay in Agriculture**; Dairy composes `scheme_revenue` into totals and
   the statement. Cost catalogue stays Dairy-owned (ADR-0013) — not moved to
   Agriculture.
5. Dependency direction: Dairy → Agriculture → Core; Dairy → Core allowed;
   Core ↛ Dairy; Agriculture ↛ Dairy; Dairy ↛ orchestration modules.

## Consequences

- Beef can later share Agriculture schemes and Core maths without importing Dairy milk.
- Hospitality can use Core without Agriculture or Dairy.
- No HTTP path, public ID, request/response, rounding, or golden-result changes.
- Future L5 should focus on orchestration/composition service seam, not further
  formula extraction.

## Related

- ADR-0013 (layer ownership)
- ADR-0014 (Core / Agriculture packages)
- `docs/architecture.md`
- `tests/test_layer_import_boundaries.py`
