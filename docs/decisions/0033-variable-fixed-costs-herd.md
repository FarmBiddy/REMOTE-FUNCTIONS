# Variable / fixed costs, gross margin and herd-size scenarios

## Status

Accepted (insights). Extends ADR-0028 and ADR-0029.

## Context

"What if I must cut my herd (nitrates derogation) or want to grow it?" cannot be
answered by scaling every cost: insurance or labour do not fall with 10 fewer
cows, feed does. Teagasc also reports variable / fixed costs and gross margin
(revenue − variable costs) next to c/L.

## Decision

1. **Dairy policy** (`dairy/costs.py`), broadly the Teagasc Profit Monitor:
   - Variable: `feed`, `fertiliser`, `vet`, `contractor`, `levies`.
   - Fixed: every other operating cost line (labour, insurance, fuel,
     electricity, water, repairs, rent, professional fees, other).
   - Herd-linked income: `cattle_sales` (calves, culls). Schemes do not move
     with cows (they are per hectare).
   A farm whose split differs adjusts with `lines_pct` in a scenario.
2. **`risk.sensitivity` `herd_pct`:** litres, variable costs and herd-linked
   income scale by `(1 + herd_pct)`; fixed costs and schemes do not. Combines
   multiplicatively with `milk_volume_pct` (yield per cow) and then `lines_pct`.
   Cash lines with the same IDs move the same way (ADR-0023).
3. **`kpi.summary`:** `per_litre_c` adds `variable_costs`, `fixed_costs`,
   `gross_margin`; `per_cow`, `per_kg_ms` and `per_hectare` add `gross_margin`.

## Consequences

- A herd cut shows the true effect: lost milk minus saved variable costs, with
  fixed costs spread over fewer litres.
- Not included: step changes in fixed costs (e.g. one less labour unit), land
  changes, per-farm custom classification.

## Related

ADR-0023, ADR-0028, ADR-0029, ADR-0032
