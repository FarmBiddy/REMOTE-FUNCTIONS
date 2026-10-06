# Report bundles (`report.bank`, `report.advisor`, `report.accountant`)

## Status

Accepted (reports)

## Context

Each audience needs a different selection of figures that already exist as
separate Engine functions. Making the Platform call five functions per report
and stitch them risks inconsistent inputs (e.g. a balance-sheet cash that does
not match the cash flow).

## Decision

1. **One input, the farm file** (`FarmReportInput`), shared by the three IDs:
   reporting `pl_months` + `cf_months` (same last month = report date),
   `opening_cash`, `milking_cows`, optional `hectares` / `milk_solids_kg`,
   `prior_pl_months`, `projected_pl_months` / `projected_cf_months` (after the
   period), `loans` (as at the report date), `assets` register, balances and
   valuations at the report date (opening livestock / stock values default to
   the closing ones), period totals `drawings` / `tax` / `off_farm_income`,
   optional `new_loan` terms and `scenarios`.
2. **Composition only.** Every section is an existing calculation's output;
   no new formulas. Derived consistency rules:
   - Balance-sheet cash = closing cash of the rolled `cf_months`.
   - Depreciation = `assets.schedule` over the reporting period.
   - Interest in net profit = `interest_paid` in `cf_months` (cash basis).
   - KPI debt balance = `loan.schedule` total balance.
3. **Bank:** net profit, KPIs (DSCR, debt per cow / ha), loans, repayment
   capacity (+ largest new loan when `new_loan` is sent, else `null`),
   balance sheet, actual cash and projection rolled on from its close.
4. **Advisor:** KPIs, net profit, variance vs `prior_pl_months` (`null` if
   none), `risk.sensitivity` on actual + projected months with shocks from the
   first projected month (ADR-0040), or on actuals only when not projected.
5. **Accountant:** P&L by line with margin, net profit bridge, fixed asset note,
   balance sheet, cash flow by line with opening / closing cash.
6. Header on every bundle: `report`, `currency`, `as_of`, `period`.
   Rendering (PDF, branding, wording) is Platform-owned.

## Consequences

- `drawings`, `tax` and `off_farm_income` are totals for the reporting period,
  not annual figures, when the period is shorter than a year.
- Not included: multi-year projections, Monte Carlo, narrative text.

## Related

ADR-0026, ADR-0028, ADR-0035, ADR-0036, ADR-0037, ADR-0038, ADR-0039, ADR-0040
