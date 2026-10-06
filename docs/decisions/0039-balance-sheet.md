# Balance sheet and ratios (`bs.summary`)

## Status

Accepted (reports)

## Context

Banks lend against net worth and security; accountants and advisors need the
balance sheet next to the P&L. Loans and fixed assets already have Engine
functions; the rest are balances and valuations only the Platform knows.

## Decision

1. Date: end of `year` / `month`.
2. Platform values (EUR at that date): `cash` (may be negative), `debtors`,
   `stock`, `livestock`, `land`, `creditors`, `other_long_term_liabilities`.
   The Engine does not value land or livestock.
3. **Loans** come in the `loan.schedule` item shape and are split here:
   principal falling due within 12 months of the date is a current liability,
   the rest non-current. **Fixed assets** come in the `assets.schedule` register
   shape and are valued at NBV at the date (assets bought later are excluded).
   The Platform never sums or splits money.
4. Layout:
   - Current assets: cash (if positive), debtors, stock.
   - Non-current assets: land, buildings, machinery, other fixed assets,
     livestock.
   - Current liabilities: overdraft (negative cash), creditors, loans due
     within 12 months.
   - Non-current liabilities: loans due after 12 months, other long-term.
   Lines are rounded first and totals summed from them, so
   assets = liabilities + net worth to the cent.
5. Ratios: net worth, equity % (net worth / assets), debt-to-assets %,
   current ratio (current assets / current liabilities, `null` without current
   liabilities), working capital. **Livestock is excluded from liquidity**:
   selling the breeding herd is not a way to pay this month's bills.

## Consequences

- Not included: accruals / prepayments detail, leases, tax liabilities,
  minority interests, multi-entity consolidation, revaluation reserves.

## Related

ADR-0025, ADR-0037, ADR-0038
