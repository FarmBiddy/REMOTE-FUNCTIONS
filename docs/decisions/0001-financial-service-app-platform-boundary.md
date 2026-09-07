# ADR-0001: Financial Service / App Platform data boundary

## Status

Accepted

## Context

Farm and user data live behind the App Platform (including Supabase/RLS). The Financial Service must calculate without becoming a second data plane.

## Decision

- The **App Platform** owns user identity, farm identity, authorization, Supabase/RLS access, farm data aggregation, and persistent financial models/scenarios.
- The **Financial Service** owns deterministic financial validation/calculation and returns structured results.
- Callers supply an explicitly scoped financial input payload. This service **MUST NOT** query Supabase or other App Platform databases to fetch source farm data.

## Consequences

- No database drivers, Supabase clients, or farm CRUD in this repository.
- Integration work belongs in the App Platform (or a dedicated BFF), which constructs inputs and consumes results.

## References

- `docs/architecture.md`
- `docs/domain-model.md`
- `docs/security.md`
