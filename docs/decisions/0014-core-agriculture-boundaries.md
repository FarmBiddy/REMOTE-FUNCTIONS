# Core and Agriculture package boundaries (L2 / L3)

## Status

Accepted (L2 Core extraction; L3 Agriculture scheme income)

## Context

L1 classified Dairy / Agriculture / Core responsibilities (ADR-0013). Physical
packages were deferred until a real Core boundary existed. Empty Agriculture
wrappers (e.g. identity functions for `land_leasing_income`) were rejected.

## Decision

1. **Core (`farm_functions.core`)** owns sector-agnostic money operations:
   Operating Surplus (`net_profit`), margins, banker's publish rounding, and
   `sum_amounts`. It must not import Agriculture, Dairy catalogues, schemas, or
   orchestration modules.
2. **Compatibility re-exports:** `farm_functions.calcs.profit` and
   `farm_functions.rounding` re-export Core so existing imports and public IDs
   stay stable.
3. **Agriculture (`farm_functions.agriculture`)** owns the canonical
   `scheme_revenue` implementation (BISS + ACRES money + other operating grants).
   Public calculation ID `revenue.schemes` is unchanged; `calcs.revenue` re-exports
   the Agriculture function.
4. **`land_leasing_income`** remains Agriculture **semantics** on the Dairy
   contract (ADR-0013); it is still composed inside Dairy `other_revenue` with no
   pass-through Agriculture function.
5. **Phase 1 operating-cost catalogue** remains Dairy-owned input vocabulary
   (ADR-0013); `total_costs` may use Core `sum_amounts` without moving field names
   to Agriculture or Core.

## Consequences

- Dependency direction: Agriculture → Core; calcs/orchestration → Agriculture/Core;
  Core ↛ Agriculture/Dairy; Agriculture ↛ Dairy/calcs.
- Beef could later call `agriculture.scheme_revenue` without importing Dairy milk.
- Hospitality can use Core without Agriculture.
- No HTTP `/v1/agriculture` surface; Dairy façade remains the product contract.

## Related

- ADR-0013 (layer ownership)
- `docs/architecture.md`
- `tests/test_layer_import_boundaries.py`
