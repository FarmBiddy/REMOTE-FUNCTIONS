# Interest-rate shocks on variable-rate loans; stress tests as presets

## Status

Accepted (analysis)

## Context

Irish farm loans are often variable-rate; the 2022–23 ECB rises raised
repayments sharply. Banks stress-test borrowers with combined shocks (milk
price down, input costs up, rates up). The Engine could shock prices, volume,
herd and lines, but not interest rates.

## Decision

1. Loan items gain `variable` (default `false`). `loan.schedule` echoes it.
2. Core `repricing_schedule(balance, months, rate_steps)`: at each step the
   remaining balance is re-amortised over the remaining months at the new rate
   (how lenders reprice variable loans). Rows before a step are unchanged.
3. **`risk.sensitivity`:** optional `loans` (the loans behind the months'
   loan lines) and per-scenario `rate_shift_pp`. Variable loans reprice by the
   shift from `shocks_from` (or their next instalment); the change in
   payment / interest / principal is added to P&L `loan_repayments` and cash
   `interest_paid` / `loan_principal_repayments`. Fixed loans are untouched.
   Operating Surplus does not change (interest is finance); DSCR and cash do.
4. **`plan.projection`:** assumption `interest_rate_shift_pp` per year (vs the
   current rate, carried forward); variable loans reprice at the start of each
   projection year. Echoed in `assumptions_used`.
5. Rates never go below 0.
6. **Stress tests are Platform presets, not Engine code.** A stress test is a
   named combination of existing shocks (e.g. "2016": milk −25%, feed +20%,
   rates +2 pp) run through `risk.sensitivity` or `plan.projection`. Like
   assumptions (ADR-0042), the Platform owns and edits the presets.

## Consequences

- The Platform must send the same loans that produced the months' loan lines.
- Not included: rate caps / floors, fixed-period expiry (fixed → variable).

## Related

ADR-0025, ADR-0029, ADR-0040, ADR-0042
