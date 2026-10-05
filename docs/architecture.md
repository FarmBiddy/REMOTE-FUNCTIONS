# Architecture

## Purpose

The Financial Service is a stateless financial calculation service.

For local workflow and **current implementation vs target architecture**, see `docs/development.md`.
Recorded decisions: `docs/decisions/`.

Its responsibility is to:
- validate financial inputs
- perform financial calculations
- return structured financial results
- expose calculation capabilities through an API

It is NOT responsible for:
- user authentication
- farm ownership
- Supabase access
- database persistence
- conversation state
- user sessions
- farm CRUD
- document ingestion

## System Boundary

The App Platform is the authoritative boundary for:
- user identity
- farm identity
- authorization
- Supabase/RLS access
- persistent financial models
- farm data aggregation

The Financial Service receives explicitly scoped financial inputs
from an authorized upstream service.

The Financial Service MUST NOT directly access Supabase.

## Data Flow

User/Agent
    ↓
App Platform
    ↓
authorized farm data
    ↓
FinancialModel (in-memory envelope) / FinancialInput
    ↓
existing calculation functions
    ↓
FinancialResult
    ↓
App Platform / Agent

HTTP still accepts a flat JSON object of numbers (see `docs/api-contract.md`). The domain types in `farm_functions/domain.py` are not a new HTTP API.

**Period contracts (ADR-0018 / P1.2–P1.4):** Annual `FinancialInput` / `pl.summary` remain the public annual facade. Monthly: flat HTTP `pl.monthly` → Application assembles `MonthlyDairyStatementModel` → `calculate_monthly_dairy_statement` → `MonthlyDairyStatementResult` (ADR-0019). Calendar identity stays on the Domain envelope/result; Core / Agriculture / Dairy formula primitives stay calendar-blind. Annual and monthly are two compositions over shared surplus, margin, rounding, scheme, and cost primitives (`tests/test_period_reconciliation.py`).

**Multi-period P&L (ADR-0020 / ADR-0021):** Near-term Engine focus is Operating Statements, then Cash Flow. **P2.1** Domain multi-month composition; **P2.2** Domain YTD; **P2.4** public HTTP `pl.months` (nested `months[]` + optional `ytd`; Domain dumps; `ytd: null` when unused). No second P&L engine, no invented months, not annual÷12, not average monthly margins. `pl.summary` and `pl.monthly` stay compatible.

**Cash Flow (ADR-0022 / P3.2):** Explicit monthly cash via `MonthlyDairyCashFlowModel` → `calculate_monthly_dairy_cash_flow` → Dairy `monthly_cash_flow` → Core cash nets. Classification (including Phase 1 `interest_paid` under financing) is Dairy catalogue policy — not Core. Operating cash lines share P&L category IDs (ADR-0023). Not derived from P&L. Public HTTP `cf.monthly` (P3.3): flat body, `year`/`month` required, every cash line optional. Cash position (ADR-0024 / P3.4): optional `opening_cash` on `cf.monthly`; `cf.months` rolls consecutive months from one opening balance (Core `closing_cash`).

**Loans (ADR-0025):** `loan.schedule` → Core `amortisation_schedule` (calendar-blind annuity rows); Application attaches periods. Rows' `interest` / `principal` are passed by the caller into `cf.*` as `interest_paid` / `loan_principal_repayments`; Cash Flow does not call loans internally.

**Forecast (ADR-0026):** `pl.forecast` / `cf.forecast` → Application `forecast.py` maps months to Core period indexes (`core/forecast.py`: run-rate, seasonal projection), applies Dairy line policy (`dairy/forecast.py`: recurring / price / known-only lines), then runs the normal monthly statement or cash flow on the projected inputs.
## Target layering (progressive)

Intended separation: **Application/API → Dairy → Agriculture → Core**, with Dairy allowed to call Core directly. Core must not know Dairy or Agriculture vocabulary.

Layer meaning (ADR-0014, ADR-0015, ADR-0016, ADR-0017):

| Layer | Package | Owns | Does not own |
|-------|---------|------|--------------|
| **Core** | `farm_functions.core` | Financial mathematics independent of farming: Operating Surplus, margins, publish rounding, `sum_amounts` | Farm field names, schemes, milk, cost catalogues |
| **Agriculture** | `farm_functions.agriculture` | Financial concepts common across agricultural enterprises (canonical `scheme_revenue` / public ID `revenue.schemes`) | Dairy milk, Dairy Operating Statement, Core maths reimplementation |
| **Dairy** | `farm_functions.dairy` | Dairy-specific specialisation: milk revenue, other-income composition, Phase 1 operating-cost catalogue, Operating Statement composition (`pl_summary`) | Generic surplus/rounding/sum; scheme formula body |
| **Application / API** | registry, provenance, runner, loaders, simulation, scenarios, `api/` | Public IDs, HTTP/domain contracts, orchestration | Financial formulas |

Dependency direction: Application/API → Dairy → Agriculture → Core (Dairy → Core also allowed). Higher/generic layers never import specialised ones.

### Execution seam (L5)

Distinct roles (do not collapse these):

| Concern | Where | Role |
|---------|-------|------|
| **Canonical implementation** | `core` / `agriculture` / `dairy` | One formula body per capability |
| **Compatibility facade** | `farm_functions.calcs.*`, `farm_functions.rounding` | Legacy re-exports only; must not grow a second formula body |
| **Capability registration** | `farm_functions.registry` (`CALCULATION_CATALOGUE`) | Public IDs, schemas, thin publish wrappers bound to canonical callables |
| **Execution orchestration** | `runner`, `api/routes`, domain/`calculate_annual_pnl`, provenance | Validate, dispatch, type, explain — no financial formulas |

HTTP path: `POST /v1/functions/<id>/run` → `runner.run_function` → registry handler → Dairy / Agriculture / Core.

Application/orchestration **must not** import `farm_functions.calcs` (ADR-0017). External code and compat tests may still use `calcs` re-exports.

- Public name `FinancialInput` stays stable; conceptually it is the **Phase 1 Dairy** input contract (do not duplicate as `DairyFinancialInput`).
- `land_leasing_income` is Agriculture semantics on that Dairy contract (ADR-0013); composed in Dairy `other_revenue` once.

Forbidden imports: Core → Agriculture/Dairy; Agriculture → Dairy/`calcs`; Dairy → orchestration; Application → `calcs`. Characterisation: `tests/test_layer_import_boundaries.py`.

No FarmBiddy DB/platform integration, multi-enterprise aggregation, Beef, or Hospitality in this service yet.

## Authentication

User JWTs MUST NOT be forwarded to the Financial Service
for the purpose of accessing Supabase.

The Financial Service uses service-to-service authentication.

## State

The calculation engine is stateless.

`FinancialModel` in this service is an in-memory envelope (`period`, `currency`, `inputs`). It is not persisted here.

Persistent financial state belongs to the App Platform.

Scenario calculations are initially ephemeral and MUST NOT
modify the persisted financial model unless an explicit
save/commit operation occurs.