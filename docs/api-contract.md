# API Contract

Canonical description of the Financial Service HTTP calculation contract.
Implementation: `farm_functions/registry.py` (authoritative catalogue), `farm_functions/runner.py`, `farm_functions/schemas.py`, `api/app.py`.

Domain types (`FinancialModel` → `FinancialInput` → calculations → `FinancialResult`) live in `farm_functions/domain.py`. They do **not** change this HTTP contract: request bodies remain a flat JSON object of numbers; statuses remain `ok` / `needs_input` / `error`.

Annual P&L provenance (`explain_annual_pnl`) is in-process only. It is not included in HTTP calculation responses.

## Calculation identifiers

Each calculation has a **stable public ID** (example: `revenue.milk`). These IDs are defined explicitly in `CALCULATION_CATALOGUE` in `farm_functions/registry.py`.

- Integrations MUST call calculations by this ID (`POST /v1/functions/<calculation_id>/run` and the `function` field in responses).
- Discovery (`GET /v1/functions`) exposes the same IDs in the `key` field.
- Internal Python handler, module, or class names are implementation details and may change independently of the public ID.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/v1/functions` | Discovery (keys, descriptions, required/optional fields) |
| `POST` | `/v1/functions/<calculation_id>/run` | Run that calculation (one concrete route per ID) |
| `POST` | `/v1/demo/pl-summary` | Demo: `pl.summary` on sample farm JSON |

Each registered calculation ID has its own path, for example:

- `POST /v1/functions/revenue.milk/run`
- `POST /v1/functions/pl.summary/run`

OpenAPI (`/docs`) documents the typed request body for each route from the Pydantic models in `farm_functions/schemas.py`. Unknown calculation IDs have no route and return **HTTP 404**.

## Calculation request

`POST /v1/functions/<calculation_id>/run`

Body: JSON object of named financial inputs (numbers). Extra / unknown fields are **rejected** (`error`). This is an **intentional breaking change** for callers that previously sent unknown or unrelated fields (they were ignored).

Missing required fields are not rejected by the HTTP layer; the runner returns `needs_input` (see below). Unknown field names are checked **before** missing required fields: if both a typo (e.g. `milk_prcie`) and a missing required field (`milk_price`) are present, the response is `error` for the unknown name, not `needs_input`.

### Zero, missing, null, and invalid

| Case | Status |
|------|--------|
| Explicit `0` | `ok` (valid zero) |
| Required field omitted | `needs_input` |
| Optional field omitted | treated as `0`, then calculated |
| Unknown / extra field (including typos and fields from another calculation) | `error` |
| `null` on a known field | `error` (invalid; not treated as missing) |
| Negative number | `error` |
| Wrong type (string, boolean, non-finite) | `error` (not coerced) |

Numeric annual P&L inputs must be **≥ 0**. No maximum is imposed unless `INPUT_FIELD_METADATA` defines one; currently every numeric `maximum` is `null`. Units in `needs_input` and in metadata come from `FIELD_UNITS`, which is derived from `INPUT_FIELD_METADATA` in `farm_functions/schemas.py`.

Published numeric results use **banker's rounding** (round half to even): money and `margin_pct` to 2 dp, `profit.margin` to 4 dp (ADR-0005).

## Response statuses

Every calculation response uses one of:

| Status | Meaning |
|--------|---------|
| `ok` | Calculation succeeded; see `result` |
| `needs_input` | Required inputs missing; nothing was guessed |
| `error` | Unknown function (via runner), unknown input fields, `null`, negatives, wrong types, or other validation failure |

Unknown function keys have no HTTP route and return **HTTP 404**; the runner itself returns `status: error` when called directly with an unknown name.

### `ok`

```json
{
  "status": "ok",
  "function": "revenue.milk",
  "result": { "amount": 200000, "currency": "EUR" }
}
```

### `needs_input`

The service **MUST NOT** guess missing financial inputs.

`missing` is a list of objects with semantic units (see ADR-0004):

```json
{
  "status": "needs_input",
  "function": "revenue.milk",
  "missing": [
    {
      "field": "milk_price",
      "unit": "EUR/litre"
    }
  ],
  "provided": ["litres_per_cow", "milking_cows"]
}
```

- `missing[].field` — input name
- `missing[].unit` — semantic unit string from `FIELD_UNITS` in `farm_functions/schemas.py`
- `provided` — sorted list of known field names that were present (string names, not objects)

### `error`

```json
{
  "status": "error",
  "function": "revenue.milk",
  "message": "One or more values are invalid.",
  "details": []
}
```

`error` covers unknown function (via the runner), unknown input field names, explicit `null`, negatives, wrong types, and other validation failures.

## Versioning

Public routes are under `/v1/`. Breaking contract changes require an explicit versioning decision and documentation update.
