# Engine scope for the platform prototype: loans, forecast, enterprises

## Status

Accepted (cash-planning; implements `loan.schedule`)

## Context

The platform prototype (Farm Financials) needs loan cards (balance, % repaid,
next instalment) and projected months (Oct–Dec). `integration-external.md`
assigned loan cards and forecast to the Platform. That would put amortisation
and projection maths in the frontend, which the Engine contract forbids
("client must not recalculate"). The prototype starts with Dairy; Sheep / wool
follows once the Dairy prototype is solid.

## Decision

1. **Loan maths belong to the Engine.** Core owns amortisation (sector-agnostic,
   calendar-blind). Loan *product data* (lender, purpose, rate type) stays
   Platform-owned and is never sent.
2. **`loan.schedule` is state-based.** Input is the loan *today*: `balance`
   outstanding, `annual_rate` (0–1 ratio, nominal, compounded monthly),
   `remaining_months`, and the calendar `year` / `month` of the next
   instalment. Optional `original_principal` adds `repaid_pct`.
   Variable-rate loans re-amortise by calling again with the current rate and
   balance; no rate history is stored or needed. One call takes `loans[]` and
   returns per-loan schedules plus portfolio totals and combined monthly debt
   service, so the Platform never sums money.
3. **Equal instalments (annuity).** Interest per month = balance × rate / 12,
   rounded to the cent (ADR-0005). The final instalment absorbs the rounding
   residue so the balance ends at exactly 0. Every row reconciles:
   `opening − principal = closing`, `interest + principal = payment`.
4. **Feeds Cash Flow by composition, not coupling.** Each row's `interest` and
   `principal` are the `interest_paid` and `loan_principal_repayments` cash
   lines (ADR-0022). The Platform passes them into `cf.monthly` / `cf.months`;
   `cf.*` does not call `loan.schedule` internally.
5. **Forecast maths belong to the Engine** (later on this branch). Projected
   months use the existing `pl.*` / `cf.*` contracts; the Engine generates the
   projected lines, the Platform renders them.
6. **Enterprises.** Current public IDs are Dairy. A future enterprise (Sheep)
   adds a package beside `dairy/` plus catalogue entries (ADR-0017). Selecting
   the enterprise over HTTP (an `enterprise` field defaulting to `dairy`, or
   namespaced IDs) is decided when Sheep starts, not now.

## Consequences

- `integration-external.md` "Platform-owned" list no longer includes loan
  maths or forecast maths.
- Not included: payment holidays, interest-only periods, balloon payments,
  fees, multiple rate steps in one call.

## Related

ADR-0005, ADR-0017, ADR-0022, ADR-0024
