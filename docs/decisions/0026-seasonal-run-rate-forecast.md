# Seasonal run-rate forecast (`pl.forecast`, `cf.forecast`)

## Status

Accepted (cash-planning)

## Context

The platform shows projected months (e.g. Oct–Dec) on the P&L chart and the
cash balance. ADR-0025 puts projection maths in the Engine. A dairy farm's year
is strongly seasonal (spring calving, peak May–June, dry Dec–Jan), so averages
or linear trends mislead. Every projected number must be traceable so Biddy and
a bank can explain it.

## Decision

Three layers, applied per line:

1. **Seasonal base:** the same month last year from the farm's own history.
2. **Run-rate:** each recurring line is scaled by
   `Σ current year / Σ same months prior year` over the months that exist in
   both years within the last 12 months of history. Prior total 0 → factor 1.
   Factors are returned (`run_rate`) so each projection is explainable.
3. **Known drivers and commitments override:** any value given on a forecast
   month replaces the projection for that line (co-op milk price, scheme
   payment dates, `loan.schedule` interest/principal, supplier invoices).

Line policy (Dairy catalogue):

- **P&L:** every operating line recurs. `milk_price` is a price, not a volume:
  it carries the latest non-zero actual unless overridden; milk revenue is then
  litres × price via the normal monthly statement. `loan_repayments` (finance)
  is not projected from history: 0 unless given.
- **Cash Flow:** operating lines recur. Investing and financing lines (a tractor
  bought last October, a loan drawn down) are one-offs: 0 unless given.

Contract:

- `{history: [actual months], forecast: [{year, month, ...known values}]}`.
  `history` items use the `pl.months` / `cf.months` item shape.
- Forecast months must be after the last history month and their same month
  last year must be in `history` (so horizon ≤ 12 months).
  Errors: `missing_prior_year_month`, `forecast_overlaps_history`,
  `duplicate_period`.
- Result: `{currency, as_of, run_rate, months[]}`; each month has `period`,
  `inputs` (projected drivers, pluggable into `pl.months` / `cf.months` beside
  actuals) and the computed `statement` / `cash_flow`.
- Core holds the calendar-blind arithmetic (period indexes, season length).

## Consequences

- Platform rolls the cash balance by sending actual + projected `inputs` to
  `cf.months`.
- No uncertainty bands: Monte Carlo / sensitivity reuse this projection as the
  central scenario (`insights`).
- Not included: herd/driver models (cows × litres per cow), multi-year horizon.

## Related

ADR-0018, ADR-0022, ADR-0024, ADR-0025
