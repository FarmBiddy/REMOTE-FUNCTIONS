# Typed response schemas in OpenAPI and discovery

## Status

Accepted (response-schemas). Completes the future work noted in ADR-0050.

## Context

OpenAPI described inputs only. The Platform hand-wrote response types, which is
how the `surplus` → `operating_surplus` rename (ADR-0050) could silently break
19 places in the UI. Generated types would make such changes fail at build
time.

## Decision

1. **One result model per public ID** in `farm_functions/responses.py`
   (`OUTPUT_MODELS`). Statement results reuse the Domain models
   (`FinancialResult`, `MonthlyDairyStatementResult`, cash-flow results).
   Models forbid extra keys; nullable fields are typed `| None`; `from` uses an
   alias.
2. **Envelopes:** each run route documents its HTTP 200 body as
   `<Id>Response` = `<Id>Ok` (`status: "ok"`, `function`, typed `result`,
   `meta`) | `NeedsInputEnvelope` | `ErrorEnvelope`.
3. **Documentation only.** Handlers still return plain dicts; FastAPI does not
   validate or filter responses at runtime (no cost, no behaviour change).
4. **Kept true by tests:** every example, happy and all-zero output is
   validated against its model with an exact round trip (`extra="forbid"`
   catches new keys, the round trip catches missing or retyped ones), and the
   three envelope kinds are validated for every ID.
5. `GET /v1/functions/{id}` adds `output_schema`.

## Consequences

- The Platform can generate TypeScript types from `/openapi.json`
  (e.g. `openapi-typescript`), so renames break the build instead of the UI.
- Changing an output now means changing its model too (the test fails
  otherwise) and bumping `ENGINE_VERSION`.

## Related

ADR-0048, ADR-0050
