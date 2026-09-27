# Period domain contract (P1.1)

## Status

Accepted (P1.1 Period Domain Contract)

## Context

P1.0 established that Phase 1 is annual-only in code, while the Mock Platform
needs true monthly Operating Statements. Monthly must not be derived as
annual ÷ 12. Approved product decisions:

- **D1 — B:** Monthly milk uses `milk_litres` + `milk_price`. Do not reuse
  annual `litres_per_cow` (litres/cow/year) with changed semantics.
- **D2 — B:** Monthly statements carry `year` + `month` for identity,
  auditability, and future multi-period reconciliation.
- **D3 — A:** Keep aggregate published income (`milk` / `schemes` / `other`)
  for the first monthly statement; finer income lines deferred to P1.5.

Architecture choice (P1.0): thin period contract above shared Core /
Agriculture / Dairy money primitives; annual `FinancialInput` /
`pl.summary` remain the compatibility facade.

## Decision

1. **Separate identity from formula inputs.** Calendar fields (`year`,
   `month`, period kind) live on the Domain statement envelope
   (`MonthlyPeriodIdentity` / `MonthlyDairyStatementModel`). Financial
   drivers live on `MonthlyDairyFinancialInput` only. Core, Agriculture,
   and Dairy formula functions remain calendar-blind.
2. **Annual contracts stay frozen.** `FinancialInput`, `FinancialModel`,
   `FinancialResult`, `Period = Literal["annual"]`, `pl.summary`, annual
   HTTP, and the €240k / €163k / €77k reference are unchanged.
3. **Monthly milk drivers differ from annual.** Required monthly milk
   fields are `milk_litres` and `milk_price`. Annual continues to use
   `milking_cows`, `litres_per_cow`, `milk_price`.
4. **Shared non-milk drivers.** Schemes, other income, operating-cost
   catalogue, and `loan_repayments` reuse the same field names as annual,
   with monthly metadata describing them as amounts for the stated month.
5. **No monthly HTTP in P1.1 / P1.2.** Types and in-process calculation only
   through P1.2. No registry ID, no HTTP monthly route, no YTD, no forecast,
   no B7/B8 changes, no income-line publication expansion.

## Consequences

- P1.2 adds in-process monthly calculation:
  `calculate_monthly_dairy_statement` → Dairy `monthly_pl_summary` /
  `milk_revenue_from_litres`, reusing Core surplus/rounding/sum and
  Agriculture `scheme_revenue`. No HTTP monthly route yet.
- Published annual `result.period` remains the string `"annual"`.
  Monthly identity uses structured `{kind, year, month}` on the monthly
  envelope and `MonthlyDairyStatementResult`.
- `profit.net` remains Operating Surplus; loans remain under `finance`.
- Monthly must never derive values by annual ÷ 12.

## Related

- P1.0 Period Semantics & Contract Audit
- ADR-0007, ADR-0009, ADR-0015, ADR-0017
- `farm_functions/domain.py`, `farm_functions/schemas.py`
