# Shared category IDs across statements (P3.2a)

## Status

Accepted (Cedric, Option A)

## Context

P3.2 named cash lines with suffixes (`feed_payments`, `milk_receipts`,
`scheme_receipts` …) while the P&L uses `feed`, `biss`, `cattle_sales` … The
Platform goal is that one tagged invoice line feeds every statement. Two
vocabularies would force a permanent translation table in the Platform.

The cash catalogue was also declared four times (category tuples, function
signature, values dict, six schema classes).

## Decision

1. **One category ID per economic line, shared by all statements.** The
   statement decides the meaning: in the P&L `feed` is the cost incurred; in
   Cash Flow `feed` is the cash paid. Invoice/accrual date → P&L, payment date →
   Cash Flow. Amounts are still explicit per statement (ADR-0022 locks hold).
2. Dairy operating cash lines:
   - In: `milk`, `biss`, `acres`, `other_grants`, `cattle_sales`,
     `land_leasing_income`, `other`
   - Out: `OPERATING_COST_CATEGORIES` (reused, not copied)
3. Investing / financing lines have no P&L counterpart and keep their names
   (`asset_disposal_proceeds`, `machinery_equipment_payments`,
   `other_capital_payments`, `loan_proceeds`, `loan_principal_repayments`,
   `interest_paid`). P&L `loan_repayments` still does not map to Cash Flow.
4. **Declare the catalogue once.** Dairy `CASH_FLOW_CATALOGUE` maps
   `(activity, direction)` → line IDs. `monthly_cash_flow(**amounts)` and the
   generated `MonthlyDairyCashFlowInput` derive from it. Adding a cash line is
   one tuple entry.

## Consequences

- Old suffix names are rejected (`extra="forbid"`). No HTTP consumer existed
  yet, so no compatibility alias.
- A new P&L operating cost automatically becomes a cash outflow line.
- `milk` in Cash Flow is a cash amount (EUR received); in the monthly P&L it is
  computed from `milk_litres × milk_price`. Same ID, different drivers.
- Sync is locked by `tests/test_monthly_cash_flow.py::test_cash_and_pnl_share_category_ids`.

## Related

ADR-0007, ADR-0013, ADR-0022
