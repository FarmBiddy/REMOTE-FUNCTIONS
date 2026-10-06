# Multi-year projection (`plan.projection`)

## Status

Accepted (projections)

## Context

Banks ask for a 3–5 year plan before a large loan (a parlour, land, herd
expansion): can the farm service its debt every year, and how do cash and
net worth develop? The monthly forecast (ADR-0026) covers 12 months only.

## Decision

1. **Annual granularity, 1–10 years (default 5).** Year 1 starts the month
   after the base; each year is 12 months.
2. **Base = the last 12 actual months** (`base_pl_months`, exactly 12
   consecutive months), totalled line by line. `opening_cash` is the bank
   balance at the end of the base.
3. **Assumptions are optional, per year, explicit lists** (index 0 = year 1):
   - `milk_price` (EUR/L); missing years carry the last given value, else the
     base average price.
   - `herd_pct`, `yield_pct`, `cost_inflation_pct`: % change in that year vs the
     previous one; missing = 0 (neutral). `lines_inflation_pct.{cost line}`
     overrides the general inflation for that line.
   - `lines_amount.{line}`: absolute EUR for an income / cost line (schemes,
     known contracts); missing years carry the last given value.
   - `drawings`, `tax`, `off_farm_income` (EUR per year); missing years carry
     the last given value, none given = 0. The Engine does not compute tax.
   Lists longer than `years` are rejected (`assumption_longer_than_years`).
   **No market opinions in the Engine:** with no assumptions the answer is
   "everything stays as in the base year". Recommended presets come from the
   Platform (market data, advisor); users edit them. Each year echoes
   `assumptions_used`.
4. **Line rules** (same as ADR-0033): litres = base × herd index × yield index;
   variable costs and herd-linked income scale with the herd index; every cost
   line scales with its inflation index; other income stays flat unless set.
5. **Debt and assets reuse the existing maths:** existing loans
   (`loan.schedule` items) and investment loans are amortised monthly and
   summed per year; depreciation and NBV come from the asset register plus
   investments (`assets.schedule`).
6. **Investments** `{year, amount, life_months, category?, loan?,
   annual_effects?}` are bought in the first month of their year (capex out,
   loan proceeds in, depreciation from that month, instalments from the next
   month); `annual_effects` (±EUR per year on operating lines) start the
   following year.
7. **Per year:** P&L (Operating Surplus, depreciation, interest, net profit
   before tax), cash (operating surplus + off-farm − drawings − tax − interest
   − principal − capex + new loans; rolled from `opening_cash`), debt (closing
   balance, debt service, DSCR = surplus / debt service, repayment cover after
   drawings and tax), simplified balance sheet (cash, fixed assets NBV, land,
   livestock = base value × herd index, debt, net worth), KPIs (cows, c/L) and
   flags (`negative_cash`, `below_min_cover` when `min_cover` is sent).

## Consequences

- Annual figures hide seasonal overdrafts: pair with the 12-month forecast.
- Working capital (debtors, stock, creditors) is assumed stable; livestock
  valuation changes are not booked as profit; land value is constant.
- Not included: uncertainty (Monte Carlo will reuse this as the central case),
  tax computation, mid-year purchase timing.

## Related

ADR-0025, ADR-0026, ADR-0031, ADR-0033, ADR-0036, ADR-0037, ADR-0038, ADR-0039
