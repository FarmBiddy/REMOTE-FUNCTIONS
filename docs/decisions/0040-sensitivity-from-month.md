# Sensitivity from a month on ("from now on")

## Status

Accepted (reports). Extends ADR-0029.

## Context

The Platform sends actual months (e.g. Jan–Sep) plus projected months
(Oct–Dec) to `risk.sensitivity`. Shocks applied to every month answered "what
if this year had been different", and a past seasonal overdraft (e.g. March,
calving) fixed the cash break-even at an unrealistic price.

## Decision

1. Optional `shocks_from_year` / `shocks_from_month` (both or neither;
   `details.reason: incomplete_period` otherwise).
2. Months before it are **history**: no price, volume, herd or line shocks.
   Investments keep their own dates (ADR-0031).
3. Break-evens use only months from the start: the milk price is the average
   of those months; the surplus break-even moves only their litres; the cash
   break-even constrains only their month-end balances (history cannot be
   rescued).
4. `lowest_cash` and `overdraft_months` look forward from the start month.
   `surplus`, `dscr` and `closing_cash` still cover all months sent.
5. Response echoes `shocks_from` (`null` when not sent: old behaviour).

## Related

ADR-0029, ADR-0031
