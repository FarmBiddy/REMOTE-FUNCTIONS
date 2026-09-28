# Cash Flow foundation decisions (P3.0 / P3.1)

## Status

Accepted (P3.0 audit decisions; P3.1 Domain/Core contracts)

## Context

Multi-period P&L (P2) is on `main`. Cash Flow is a **new** Engine capability,
independent of Operating Statements. P3.0 audited IAS 7 / Teagasc / Engine
boundaries. Cedric approved product decisions D-CF1–D-CF5 below.

Phase 1 Cash Flow is **management cash flow** (explicit movements for charts and
farm decisions). It is **not** an IAS 7–compliant Statement of Cash Flows.

## Decision

### D-CF1 — Interest classification is policy, not Core arithmetic

Core must **not** hard-code “interest = financing” (or operating). Core only
provides sector-agnostic cash arithmetic (sums and nets of already-monetary
amounts) plus optional activity/direction **literals** for typed composition.

Where `interest_paid` sits in a Phase 1 Dairy statement is a **composition /
accounting-policy** choice owned by Domain/Dairy catalogues. Phase 1 Dairy
places `interest_paid` under the **financing outflows** group of the monthly
cash **input** model for prototype clarity. That grouping may change under a
later policy ADR without changing Core maths.

### D-CF2 — Investing and financing from Phase 1

Phase 1 includes a **small** investing and financing catalogue, not
operating-only charts. Minimum fields:

- Investing in: `asset_disposal_proceeds`
- Investing out: `machinery_equipment_payments`, `other_capital_payments`
- Financing in: `loan_proceeds`
- Financing out: `loan_principal_repayments`, `interest_paid` (see D-CF1)

### D-CF3 — Opening / closing cash deferred

`cash_in` / `cash_out` / `net_cash_flow` first. Opening cash, closing cash, and
`opening + net = closing` reconciliation wait for **P3.4**.

### D-CF4 — Household drawings later

Not in Phase 1 Engine catalogues. Not permanently “Platform-only”: future Engine
cash semantics may include drawings/living as a later gate (family-farm cash
management). Do not add now.

### D-CF5 — Implement from P2-on-main

Cash Flow work proceeds on a branch based on updated `main` after multi-period
P&L merge (branch in use: `cashflow`).

### Additional locks (P3.0)

1. Cash Flow must **not** derive movements from P&L by annual÷12 or silent
   accrual→cash mapping. Explicit cash inputs only.
2. P&L `loan_repayments` must **not** auto-map into Cash Flow (no principal /
   interest split there).
3. Direct-method-compatible architecture (gross inflows/outflows by class).
4. Reuse `MonthlyPeriodIdentity` pattern: calendar on envelope, not Core.
5. No HTTP, multi-month cash, or Mock changes in P3.1 (calculation arrives in P3.2).

### P3.1 scope

- Core: cash direction/activity literals; `cash_section_net` / `net_cash_flow`
  (in − out) using existing `sum_amounts` where useful; banker's `round_money`
  remains available.
- Domain/schemas: Phase 1 monthly Dairy cash **input** catalogues and
  **result** contract shapes; envelope `MonthlyDairyCashFlowModel`.
- **No** registry/HTTP in P3.1.

### P3.2

- Dairy `monthly_cash_flow` + Domain `calculate_monthly_dairy_cash_flow`.
- No HTTP, multi-month cash, or opening/closing cash.

## Consequences

- P3.2 composes Dairy monthly cash from these contracts using Core nets.
- Interest policy can move between O/I/F groups later without Core rewrites.
- P&L public IDs and Operating Surplus remain unchanged.

## Related

- P3.0 Cash Flow Foundation Audit
- ADR-0007 (P&L finance separation), ADR-0018 (period identity), ADR-0020 (multi-period P&L)
- IAS 7 / Teagasc citations in the P3.0 audit report
