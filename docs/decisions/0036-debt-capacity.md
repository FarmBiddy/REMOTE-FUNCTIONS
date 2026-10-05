# Repayment capacity and borrowing capacity (`debt.capacity`)

## Status

Accepted (insights)

## Context

"How much can I borrow?" is the first bank question. Lenders assess what the
household can repay after living costs and tax, not just the farm surplus,
and they keep headroom above current debt service.

## Decision

1. Input: assessment `months` (pl.months items, actual or projected, usually
   12), optional period totals `drawings`, `tax`, `off_farm_income`, and the
   new loan's `annual_rate`, `term_months` and `min_cover` (≥ 1, default 1).
2. **Repayment capacity** = Operating Surplus + off-farm income − drawings −
   tax. **Debt service** = P&L `loan_repayments` of the months.
   **Repayment cover** = capacity / debt service (`null` without debt).
3. **Largest new loan:** total debt service the lender accepts is
   capacity / `min_cover`; headroom = that − current debt service (≥ 0);
   monthly headroom = headroom / months; principal = inverse annuity
   (Core `annuity_principal`) at the rate and term, **rounded down** to the cent
   so its instalment never exceeds the headroom.
4. Tax and drawings are inputs: the Engine does not compute tax, and the
   household budget is Platform data. `min_cover` is lender policy, passed in.

## Consequences

- Use projected months (`pl.forecast` inputs) for a forward-looking assessment.
- DSCR in `kpi.summary` (surplus / repayments) and repayment cover here differ
  on purpose: the latter is after drawings and tax.
- Not included: security / loan-to-value, stress tests on the new loan (use
  `risk.sensitivity` with an investment), interest-only periods.

## Related

ADR-0025, ADR-0028, ADR-0030, ADR-0031
