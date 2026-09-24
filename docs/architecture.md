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

## Target layering (progressive)

Intended separation: **Orchestration / API → Dairy → Agriculture → Core**, with Dairy allowed to call Core directly. Core must not know Dairy or Agriculture vocabulary.

Implemented packages (ADR-0014, ADR-0015):

| Layer | Package | Owns |
|-------|---------|------|
| Core | `farm_functions.core` | Operating Surplus, margins, publish rounding, `sum_amounts` |
| Agriculture | `farm_functions.agriculture` | Canonical `scheme_revenue` (public ID `revenue.schemes`) |
| Dairy | `farm_functions.dairy` | Milk revenue, other-income composition, operating-cost catalogue, Phase 1 Operating Statement (`pl_summary`) |
| Orchestration | registry, provenance, runner, loaders, simulation, scenarios, API | Public IDs, contracts, coordination — not financial formulas |

- Public name `FinancialInput` stays stable; conceptually it is the **Phase 1 Dairy** input contract (do not duplicate as `DairyFinancialInput`).
- `land_leasing_income` is Agriculture semantics on that Dairy contract (ADR-0013); composed in Dairy `other_revenue` once.
- Compatibility re-exports: `calcs.*` and `farm_functions.rounding` preserve existing imports; one implementation each.

Forbidden imports: Core → Agriculture/Dairy; Agriculture → Dairy/`calcs`; Dairy → orchestration (`calcs` is re-export only). Characterisation: `tests/test_layer_import_boundaries.py`.

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