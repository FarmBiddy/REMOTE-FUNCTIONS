# Canonical Phase 1 annual Operating Statement (`pl.summary`)

## Status

Accepted (Workstream B4)

## Context

Workstream B2 delivered the Phase 1 Operating Surplus model and finance separation
(ADR-0007). Atomic catalogue IDs remain useful for schedules, discovery, and tests.
B4 records which surface is the **authoritative annual Operating Statement** and
reaffirms naming Option A so integrations do not treat B4 as a model redesign.

## Decision

1. **Canonical annual view:** `pl.summary` is the Phase 1 canonical annual Operating
   Statement. It is the only public calculation that returns the full
   `{currency, period, revenue, costs, profit, finance}` annual view. In-process
   `calculate_annual_pnl` wraps the same composition; it does not introduce alternate
   maths.
2. **Supporting schedules:** Atomic IDs (`revenue.*`, `costs.total`, `profit.net`,
   `profit.margin`) remain first-class public calculations. For the same inputs,
   their published results must reconcile with the corresponding `pl.summary` fields
   under ADR-0005 publication rounding.
3. **Naming Option A:** Keep public IDs `profit.net` and `profit.margin`. Their
   Phase 1 meaning remains Operating Surplus / Operating Surplus margin (ADR-0007).
   Do not add aliases or rename IDs in B4. Keep the `pl.summary` ID.
4. **Output shape:** No JSON reorganisation in B4. Finance stays separate;
   `loan_repayments` does not reduce Operating Surplus.
5. **Scope:** B4 does not add categories, KPIs, cash flow, balance sheet, depreciation,
   tax, drawings, capex, livestock valuation, forecasting, scenarios, benchmarking,
   advisory warnings, persistence, or authentication.

## Consequences

- Documentation and catalogue descriptions treat `pl.summary` as the authoritative
  annual statement; atomic IDs are schedules that must reconcile to it.
- Callers building a full annual view should prefer `pl.summary` (or
  `calculate_annual_pnl` in-process).
- Characterisation tests may lock `pl.summary` ↔ component reconciliation without
  changing formulas.

## Related

- ADR-0005 (banker's rounding), ADR-0007 (Operating Surplus / finance)
- ADR-0010 (Phase 1 provenance / explainability assembly)
- `docs/api-contract.md`, `docs/domain-model.md`, README
- `farm_functions/calcs/summary.py`, `farm_functions/domain.py`, `farm_functions/registry.py`
