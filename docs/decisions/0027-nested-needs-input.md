# Nested `needs_input` with paths

## Status

Accepted (cash-planning). Supersedes the "nested missing required driver"
row of ADR-0021 D6.

## Context

`pl.months`, `cf.months`, `loan.schedule` and the forecasts take nested arrays.
A missing required field inside an item (e.g. `milk_price` in the fourth month)
returned `error`, so Biddy could not ask the farmer for it. Missing values must
be asked for, never guessed (ADR-0004).

## Decision

1. When the **only** validation problems are missing required fields (top-level
   or nested), the status is `needs_input`.
2. Nested `missing` entries add `path` in caller terms:
   `{"field": "milk_price", "unit": "EUR/litre", "path": "months[3].milk_price"}`.
   Indexes are positions in the request array. Top-level entries keep the
   ADR-0004 shape `{field, unit}`.
3. If any other problem is present (negative, null, wrong type, unknown field,
   period errors), the status stays `error`: fix the bad value first.
4. Issues carry `code: missing_required`, `field` = leaf name and
   `details.path`.

## Consequences

- Clients key nested prompts on `path`; `field` + `unit` still drive the
  question wording.
- Purely additive for top-level `needs_input`.

## Related

ADR-0004, ADR-0021
