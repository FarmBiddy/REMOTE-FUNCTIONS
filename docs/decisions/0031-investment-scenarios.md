# Investment scenarios ("Can I afford it?")

## Status

Accepted (insights). Extends ADR-0029.

## Context

The most valuable farm decision question is whether a capital purchase (a
parlour, a tractor) is affordable: what it does to cash, to debt cover and to
the milk price the farm can withstand. All the pieces existed separately
(`loan.schedule`, cash roll-forward, break-evens).

## Decision

1. `risk.sensitivity` scenarios take up to 5 `investments`:
   `{year, month, amount, cash_line?, loan?: {amount, annual_rate,
   remaining_months}, monthly_effects?: {line: ±EUR per month}}`.
   The purchase month must be inside `cf_months`.
2. **Purchase month:** `amount` is a cash outflow on `cash_line`
   (`other_capital_payments` by default, or `machinery_equipment_payments`).
   Capex is never an operating cost. A loan adds `loan_proceeds` that month.
3. **Loan:** Core amortisation, first instalment the month after purchase.
   Interest / principal go to the cash lines; the instalment goes to P&L
   `loan_repayments`, so DSCR reflects the new debt.
4. **Monthly effects** start the month after purchase and apply to P&L and
   cash alike (shared line IDs, ADR-0023). Lines are the operating lines except
   milk (use volume / price shocks); values below 0 floor at 0.
5. **Per investment:** `loan_monthly_payment`, `monthly_benefit` (income
   effects − cost effects) and `simple_payback_months` = amount / benefit
   (`null` when there is no positive benefit). Payback looks past the forecast
   horizon, which is usually shorter than the asset's life.
6. **Break-evens are reported per scenario** (moved from the top level of
   ADR-0029): "with the parlour, below what price do I go overdrawn?".
7. Shocks apply after investments, so "parlour + milk −5c" is one scenario.

## Consequences

- Not included: NPV / IRR, depreciation, grants towards capex (pass them as a
  negative-cost effect or reduce `amount`), residual value, tax relief.

## Related

ADR-0025, ADR-0029
