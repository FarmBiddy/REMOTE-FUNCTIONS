# Monthly Operating Statement HTTP contract (`pl.monthly`)

## Status

Accepted (P1.4)

## Context

P1.1–P1.3 established the monthly Domain envelope and in-process calculation
that reuse Core / Agriculture / Dairy primitives without annual ÷ 12. External
clients (Mock Platform) needed a public HTTP calculation ID without learning
Domain type construction or internal packages.

## Decision

1. **Public ID:** `pl.monthly` (two-segment catalogue style, parallel to
   `pl.summary`). Do not nest as `pl.summary.monthly`. Do not rename
   `pl.summary`.
2. **Transport:** Flat JSON including `year`, `month`, and monthly financial
   drivers. Application/registry assembles `MonthlyPeriodIdentity` +
   `MonthlyDairyFinancialInput` → `calculate_monthly_dairy_statement`.
3. **No formulas in Application.** Adapter is envelope assembly only.
4. **Errors:** Existing `needs_input` / `error.code` vocabulary; calendar
   range failures map to `invalid_type`.
5. **CORS / routing:** Same Application middleware and
   `POST /v1/functions/<id>/run` pattern as annual.

## Consequences

- Catalogue has nine public IDs; discovery and OpenAPI auto-include `pl.monthly`.
- Annual `POST /v1/functions/pl.summary/run` request/response unchanged.
- Future YTD can use a separate ID (e.g. `pl.ytd`) without nesting under annual.
- No YTD, forecast, simulation/scenario HTTP, or persistence in P1.4.

## Related

- ADR-0018 (period Domain contract)
- ADR-0009 (canonical annual `pl.summary`)
- `docs/integration-external.md`
- `tests/test_external_integration_http.py`
