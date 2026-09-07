# API Contract

Canonical description of the Financial Service HTTP calculation contract.
Implementation: `farm_functions/runner.py`, `farm_functions/schemas.py`, `api/app.py`.

Domain types (`FinancialModel` → `FinancialInput` → calculations → `FinancialResult`) live in `farm_functions/domain.py`. They do **not** change this HTTP contract: request bodies remain a flat JSON object of numbers; statuses remain `ok` / `needs_input` / `error`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/v1/functions` | Discovery (keys, descriptions, required/optional fields) |
| `POST` | `/v1/functions/{name}/run` | Run a named calculation |
| `POST` | `/v1/demo/pl-summary` | Demo: `pl.summary` on sample farm JSON |

## Calculation request

`POST /v1/functions/{name}/run`

Body: JSON object of named financial inputs (numbers). Extra fields are ignored.

## Response statuses

Every calculation response uses one of:

| Status | Meaning |
|--------|---------|
| `ok` | Calculation succeeded; see `result` |
| `needs_input` | Required inputs missing; nothing was guessed |
| `error` | Unknown function (via runner), invalid types, or other failure |

Unknown function names via the HTTP route return **HTTP 404**; the runner itself returns `status: error` when called directly.

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
  "message": "One or more values are not valid numbers.",
  "details": []
}
```

## Versioning

Public routes are under `/v1/`. Breaking contract changes require an explicit versioning decision and documentation update.
