# Net profit before tax (`pl.net`)

## Status

Accepted (reports). Builds on ADR-0007 (Operating Surplus is not net profit).

## Context

Accountants and banks read net profit, not Operating Surplus. ADR-0007 kept
depreciation, interest and valuation changes out of the Operating Statement;
`assets.schedule` (ADR-0037) and `loan.schedule` (ADR-0025) now provide them.

## Decision

1. Input: `months` (pl.months items) plus period totals: `depreciation`,
   `interest`, and opening / closing `livestock` and `stock` (feed, fertiliser
   in store) values. All default to 0.
2. Bridge (published as separate lines):
   - Operating Surplus (normal monthly statements)
   - ± livestock value change (closing − opening) ± stock value change
   - = adjusted surplus − depreciation = **EBIT** − interest
   - = **net profit before tax**; net margin = net profit / revenue (`null`
     without revenue).
3. **Only interest is an expense.** Loan principal is financing and never
   reduces profit; P&L `loan_repayments` are ignored here.
4. Depreciation and interest are inputs, normally passed straight from
   `assets.schedule` `total.depreciation` and the period's `loan.schedule`
   `interest`: composition, not recalculation. Valuations are Platform data
   (the Engine does not value livestock).
5. Tax and drawings sit below this line and are not deducted.

## Consequences

- Operating Surplus stays the operating KPI; `pl.net` is the accounting view.
- Not included: tax, gains / losses on asset disposals, accrual adjustments
  (debtors / creditors timing).

## Related

ADR-0007, ADR-0025, ADR-0030, ADR-0037
