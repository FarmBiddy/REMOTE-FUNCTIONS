# Cash position and multi-month roll-forward (P3.4)

## Status

Accepted

## Context

ADR-0022 (D-CF3) deferred opening / closing cash. Without them the Engine
cannot answer "how much cash will I have in month X?", which is the main
farm cash-flow question (seasonal milk, spring calving months with no milk
cheque) and the first thing a bank checks.

## Decision

1. **Core** `closing_cash(opening, net) = opening + net`. No farm vocabulary.
2. **`opening_cash` is a position, not a movement.** It lives on the Domain
   envelope (not in the cash line catalogue) and **may be negative**
   (overdraft). Cash lines stay ≥ 0.
3. **`cf.monthly`**: optional `opening_cash`. When supplied, the result has
   `opening_cash` and `closing_cash`; otherwise both are `null`.
4. **`cf.months`**: `{opening_cash (required), months[]}`. Each item uses the
   `cf.monthly` fields without `opening_cash`. Months are sorted
   chronologically and must be **consecutive** (Dec → Jan crosses years).
   Gaps → `error`, `details.reason = "non_contiguous_months"`; duplicates →
   `duplicate_period`. A gap would hide movements and misstate the balance.
5. Each month opens with the previous month's **published** closing cash.
   Rolling on published (rounded) figures keeps `opening + net = closing`
   exact to the cent in every month.
6. Result: `{currency, opening_cash, months[], cash_in, cash_out,
   net_cash_flow, closing_cash}`; period `closing_cash` = last month's closing.

## Consequences

- Platform must supply the bank position at the start of the first month
  (Biddy can ask for it via `needs_input`, unit EUR).
- Forecast months use the same contract: explicit projected cash lines per
  month. Projection logic stays outside this ADR.
- Not included: household drawings (D-CF4), multiple bank accounts, VAT.

## Related

ADR-0022, ADR-0023, ADR-0005 (banker's rounding)
