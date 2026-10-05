# Dairy KPIs (`kpi.summary`)

## Status

Accepted (insights)

## Context

The platform's "Am I profitable?" and "Can I pay my loans?" tiles compared
totals in the frontend. Farmers, co-ops, Teagasc and banks judge a dairy farm
by unit costs and debt cover, not by totals alone. The README listed KPIs as out
of scope for Phase 1; the prototype now needs them.

## Decision

1. **Input reuses the monthly contract:** `{months: [pl.months items],
   milking_cows}`. Months may be actual or projected (`pl.forecast` `inputs`),
   any order, no duplicates, gaps allowed (the KPI covers exactly the months
   sent). `milking_cows` is the average milking herd over those months.
2. **Totals** come from the normal monthly statements, summed (no second P&L).
3. **KPIs:**
   - Per litre, in **cents** (c/L): revenue, operating costs, every cost line,
     Operating Surplus. Divisor = `milk_litres` sold.
   - Per cow, in EUR: litres, revenue, costs, surplus.
   - **DSCR** = Operating Surplus / loan repayments. Operating Surplus excludes
     loan repayments and interest (ADR-0007), so it is the amount available for
     debt service.
4. **Undefined ratios are `null`** (no litres, no cows, no repayments), never 0.
   A loss gives a negative surplus and a negative DSCR.
5. Ratio arithmetic is Core (`per_unit`, `coverage_ratio`); c/L and the Dairy
   KPI set are Dairy.
6. **No thresholds or traffic lights in the Engine.** What DSCR a lender
   requires is lender policy; the Platform / Biddy interpret the number.

## Consequences

- KPIs over a forecast: send actual + projected months together.
- kg MS, per-hectare and debt ratios: ADR-0032. Not included: stocking rate,
  benchmarks against other farms.

## Related

ADR-0007, ADR-0020, ADR-0026
