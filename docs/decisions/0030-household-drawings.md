# Household drawings in Cash Flow

## Status

Accepted (insights). Implements ADR-0022 D-CF4.

## Context

On a family farm the household lives off the farm account. Without drawings,
projected cash (and every overdraft warning) is too optimistic. ADR-0022
deferred drawings to "a later gate"; the cash planning prototype now needs them.

## Decision

1. New cash line `household_drawings` (EUR, ≥ 0) under **financing outflows**:
   money the owner takes out of the business, like a distribution. It is
   never an operating cost and never on the P&L (ADR-0007); `pl.*` rejects it.
2. **Forecast:** unlike other financing lines, drawings recur, so `cf.forecast`
   projects them from the same month last year × run-rate (ADR-0026).
3. **Sensitivity:** `lines_pct.household_drawings` shocks it like any line.
4. Only one figure per month. Splitting by purpose (school, car …) is Platform
   data; tax on drawings is out of scope.

## Consequences

- DSCR stays Operating Surplus / loan repayments (bank convention). Drawings
  show up in cash, not in DSCR.

## Related

ADR-0007, ADR-0022, ADR-0026, ADR-0029
