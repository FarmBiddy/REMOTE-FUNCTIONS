# KPIs per kg milk solids, per hectare and debt

## Status

Accepted (insights). Extends ADR-0028.

## Context

Irish co-ops pay on milk solids and Teagasc benchmarks costs per kg of milk
solids (kg MS) and margins per hectare. Banks and advisors look at debt per cow
and per hectare. `kpi.summary` only had c/L and per cow.

## Decision

1. Three **optional** period inputs on `kpi.summary`, all totals for the months
   sent: `milk_solids_kg` (kg MS sold), `hectares` (farmed area) and
   `debt_balance` (outstanding loans, e.g. `loan.schedule` `total_balance`).
   The monthly item shape is unchanged.
2. Outputs: `per_kg_ms` {revenue, costs, surplus} in EUR/kg MS;
   `per_hectare` {milk_litres, revenue, costs, surplus};
   `debt` {balance, per_cow, per_hectare}.
3. A block is `null` when its input was not sent; a single ratio is `null` when
   its divisor is 0 (ADR-0028).
4. **No debt per litre.** Debt is a balance; dividing it by the litres of a
   partial period (e.g. a quarter) would overstate it. Debt ratios use stock
   measures only (cows, hectares).

## Consequences

- Per-hectare and per-kg-MS money figures cover the months sent, like c/L.
- Not included: stocking rate (cows/ha), kg MS per cow targets, benchmarks.

## Related

ADR-0028
