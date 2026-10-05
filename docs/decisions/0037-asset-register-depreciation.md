# Fixed asset register and depreciation (`assets.schedule`)

## Status

Accepted (reports)

## Context

Net profit, the balance sheet and the accountant report all need depreciation
and the net book value (NBV) of machinery and buildings. Capex already moves
cash (ADR-0031) but was never spread over the asset's life.

## Decision

1. Input: `assets[]` (≤ 200) `{category (machinery | buildings | other),
   cost, year, month (acquired), method, life_months? , residual_value?,
   annual_rate?}` and the period `from_year/from_month` – `to_year/to_month`.
2. Methods:
   - `straight_line` (default): equal monthly charge `(cost − residual) /
     life_months`, never below `residual_value`. Needs `life_months`.
   - `reducing_balance`: `annual_rate` of the remaining value per year,
     applied monthly as `cost × (1 − rate)^(months / 12)`. Needs `annual_rate`.
3. Depreciation starts in the acquisition month. Assets bought after the period
   are not held (all zero).
4. Output per asset (input order), per category and in total: the fixed asset
   note `opening_nbv + additions − depreciation = closing_nbv`. Opening and
   closing NBV are rounded first and depreciation derived from them, so every
   note reconciles to the cent and consecutive periods chain exactly.
5. Core holds the calendar-blind NBV formulas; the Application layer maps
   calendar months and builds the note.

## Consequences

- Platform owns the register (names, serial numbers, which asset is which);
  results come back in input order.
- Not included: disposals and gains/losses on sale, revaluations, impairment,
  tax capital allowances (accountant territory), land (not depreciated; its
  value goes straight to the balance sheet).

## Related

ADR-0005, ADR-0031
