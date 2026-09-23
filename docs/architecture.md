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

## Target layering (progressive; not fully packaged yet)

Intended long-term separation: **Dairy → Agriculture → Core**, with Dairy allowed to call Core directly. Core must not know Dairy or Agriculture vocabulary.

Phase 1 ownership (ADR-0013):

- Farmer-entered operating-cost catalogue lines on `FinancialInput` are **Dairy-owned** until shared-farm / multi-enterprise work needs an Agriculture catalogue.
- `land_leasing_income` has **Agriculture** semantics (lease land out) but remains on the current Dairy contract and `revenue.other` composition.
- Core performs generic money operations (e.g. Operating Surplus, margins, rounding) without owning sector field names.

Package folders `core/` / `agriculture/` / `dairy/` are not required until L2+ extraction; do not duplicate farmer inputs across layers.

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