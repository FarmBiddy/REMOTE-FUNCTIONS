# Driver ranking (`risk.tornado`)

## Status

Accepted (analysis)

## Context

Farmers and advisors need to know which risks matter most before choosing
scenarios, ranges or hedges. A tornado chart (one driver at a time, down and
up) is the standard, explainable answer and also tells Monte Carlo which
drivers deserve a distribution.

## Decision

1. Input: the `risk.sensitivity` base (`pl_months`, `cf_months`,
   `opening_cash`, `loans`, `shocks_from_*`), `step_pct` (default 10, in
   (0, 100]), `rate_step_pp` (default 1) and `rank_by`
   (`surplus` | `closing_cash` | `lowest_cash`, default `surplus`).
2. Drivers, each moved down and up by the step while everything else stays at
   base:
   - milk price (± step % of the base average price, reported in c/L),
   - milk volume and herd size (± step %, herd rules of ADR-0033),
   - every operating income line except milk, every operating cost line and
     `household_drawings` **that has an amount** in the months sent,
   - interest rate (± `rate_step_pp`) only when a loan is `variable`.
3. Every point runs through `risk.sensitivity` (no new maths). Each driver
   returns `low` / `high` outcomes (surplus, closing cash, lowest cash, DSCR)
   and `swing` = |high − low| per metric; drivers are sorted by
   `swing[rank_by]`, largest first.

## Consequences

- Swings depend on the step: compare drivers only within one call.
- Not included: asymmetric ranges per driver, interactions between drivers
  (use scenarios or Monte Carlo).

## Related

ADR-0029, ADR-0033, ADR-0040, ADR-0043
