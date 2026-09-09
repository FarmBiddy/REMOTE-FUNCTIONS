# API Contract

Canonical description of the Financial Service HTTP calculation contract.
Implementation: `farm_functions/registry.py` (authoritative catalogue), `farm_functions/runner.py`, `farm_functions/schemas.py`, `api/app.py`.

Domain types (`FinancialModel` → `FinancialInput` → calculations → `FinancialResult`) live in `farm_functions/domain.py`. They do **not** change this HTTP contract: request bodies remain a flat JSON object of numbers; statuses remain `ok` / `needs_input` / `error`.

Annual P&L provenance (`explain_annual_pnl`) is in-process only. It is not included in HTTP calculation responses.

## Contract snapshot

**Service:** Stateless annual dairy P&L calculator (validate inputs, run named calculations, return structured results).

**Calculations (8 public IDs):** `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`, `pl.summary` — from `CALCULATION_CATALOGUE` only.

**Inputs:** Flat JSON numbers per calculation. Required fields → `needs_input` when omitted. Optional omitted → `0`. Explicit `0` is valid. Unknown fields / null / negatives / wrong types → `error` with stable codes. Units come from `FIELD_UNITS` / `needs_input` / metadata — **not** from discovery.

**Outputs:** Money calculations → `{amount, currency:"EUR"}`. `profit.margin` → margin object. `pl.summary` / in-process `FinancialResult` → `{currency, period, revenue, costs, profit}` with `period:"annual"`.

**Validation:** Codes `missing_required`, `unknown_field`, `null_not_allowed`, `negative_value`, `invalid_type`, `non_finite_value`, `unknown_calculation`. Branch on `error.code`, not message text.

**Precision:** Internal `float` (ADR-0006); publish with banker's rounding (ADR-0005); published aggregate totals are authoritative; rounded lines need not re-sum exactly; provenance stays unrounded.

**Provenance:** In-process for seven catalogue entries with `supports_provenance=True` (`pl.summary` excluded). Not on HTTP.

**Out of scope here:** persistence, authentication, scenarios, forecasting, monthly cashflow, KPIs, multi-currency, multi-period, AI-generated calculations, Supabase/farm CRUD.

### Intentional interface differences

| Layer | Representation |
|-------|----------------|
| HTTP / runner | Flat per-calculation field dict |
| Domain | `FinancialModel` envelope (`period`, `currency`, `inputs: FinancialInput`) for in-process annual P&L only |
| Discovery | `key`, `description`, `required`, `optional` — no units (by design) |
| Provenance | Unrounded formula values; published API results are rounded |

Do **not** force HTTP to accept `FinancialModel`, and do not treat discovery as a full unit dictionary.

## Current Financial Domain Contract Scope

**Freeze status (branch `FINANCIAL-DOMAIN-CONTRACT`):** technical contract ready for review. This branch has **not** been merged into `main`. Workstream B financial semantics remain open separately.

### Included

- Deterministic annual dairy P&L calculation service
- Eight stable public calculation IDs via `CALCULATION_CATALOGUE`
- Typed in-process domain (`FinancialInput` / `FinancialModel` / `FinancialResult` / `calculate_annual_pnl`)
- Strict input validation, units metadata, structured errors
- In-process provenance for seven calculations
- Public HTTP discovery and execution (`/v1/functions`, `/run`, demo)
- Reconciliation, golden/reference, error, precision, and alignment regression tests
- Publication rounding (ADR-0005) and Phase 1 float precision policy (ADR-0006)

### Not included (do not assume)

- Workstream B financial semantic redesign (`profit.net` meaning, `loan_repayments` principal vs interest)
- Scenarios / Base–Best–Worst / sensitivity / forecasting
- Monthly cash flow, balance sheet, KPIs, valuation, optimisation
- Persistence, database, authentication, farm identity
- Accounting / banking / CRM integrations
- Multi-currency, multi-period
- HTTP provenance or HTTP `FinancialModel` as the request body
- AI-generated financial calculations / broader platform orchestration

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

OpenAPI (`/docs`) documents the typed request body for each catalogue ID. Unknown calculation IDs are handled by a catch-all route (not listed in OpenAPI) that returns **HTTP 404** with structured `unknown_calculation` body.

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

Published numeric results use **banker's rounding** (round half to even): money and `margin_pct` to 2 dp, `profit.margin` to 4 dp (ADR-0005). Internal calculation inputs and formulas use `float`; publication rounding is separate from internal precision (ADR-0006). Aggregate published totals are authoritative; independently rounded line items need not re-sum exactly to those totals.

Monetary **line items** (for example `pl.summary.costs.lines`) are each published with an independent `round_money` call. Aggregate **totals** (for example `costs.total` / `pl.summary.costs.total`) are calculated from the underlying full-precision values and rounded once at publication. Because rounding is applied independently for presentation, re-summing published line items may occasionally differ from the published aggregate total by a small rounding amount. Integrations **must** treat the published aggregate `total` as authoritative.

## Response statuses

Every calculation response uses one of:

| Status | Meaning |
|--------|---------|
| `ok` | Calculation succeeded; see `result` |
| `needs_input` | Required inputs missing; nothing was guessed |
| `error` | Unknown function (via runner), unknown input fields, `null`, negatives, wrong types, or other validation failure |

Unknown function keys return **HTTP 404** with structured `unknown_calculation` (catch-all; catalogue routes stay typed in OpenAPI). The runner returns `status: error` with the same code when called directly with an unknown name.

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

`missing` is a list of objects with semantic units (see ADR-0004). Structured `error` / `errors` with code `missing_required` are also present so integrations can branch on a stable code without parsing message text:

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
  "provided": ["litres_per_cow", "milking_cows"],
  "error": {
    "code": "missing_required",
    "message": "milk_price is required",
    "field": "milk_price"
  },
  "errors": [
    {
      "code": "missing_required",
      "message": "milk_price is required",
      "field": "milk_price"
    }
  ]
}
```

- `missing[].field` — input name
- `missing[].unit` — semantic unit string from `FIELD_UNITS` in `farm_functions/schemas.py`
- `provided` — sorted list of known field names that were present (string names, not objects)
- `error` / `errors` — structured issues (see Error codes). `missing` remains the ADR-0004 list with units.

### `error`

Invalid or unsupported supplied input (or unknown calculation via the runner):

```json
{
  "status": "error",
  "function": "costs.total",
  "message": "One or more values are invalid.",
  "error": {
    "code": "negative_value",
    "message": "feed must be greater than or equal to 0",
    "field": "feed",
    "value": -1,
    "details": { "minimum": 0 }
  },
  "errors": [
    {
      "code": "negative_value",
      "message": "feed must be greater than or equal to 0",
      "field": "feed",
      "value": -1,
      "details": { "minimum": 0 }
    }
  ]
}
```

- `error` — primary issue (deterministic: sort by `field`, then `code`)
- `errors` — full list of issues when several fields fail
- Irrelevant keys (`field`, `value`, `details`) are omitted when not applicable
- Top-level `message` is human-readable and **may evolve**; machine integrations MUST branch on `error.code` / `errors[].code`, not on message text

Unknown calculation via the runner (no HTTP route match handled separately below):

```json
{
  "status": "error",
  "message": "Unknown function: does.not.exist",
  "error": { "code": "unknown_calculation", "message": "Unknown function: does.not.exist" },
  "errors": [{ "code": "unknown_calculation", "message": "Unknown function: does.not.exist" }]
}
```

HTTP unknown calculation ID: **404** with the same structured body (not a bare FastAPI `detail` string).

## Error codes

| Code | Meaning | Typical status |
|------|---------|----------------|
| `missing_required` | Required known field omitted | `needs_input` |
| `unknown_field` | Unsupported input name (typo or wrong calculation) | `error` |
| `null_not_allowed` | Explicit null not accepted | `error` |
| `negative_value` | Value below current minimum (0) | `error` |
| `invalid_type` | Invalid type (string, boolean, non-object body, etc.) | `error` |
| `non_finite_value` | NaN / infinity on the Python runner path | `error` |
| `unknown_calculation` | Calculation ID does not exist | `error` / HTTP 404 |

Successful calculation response contracts (`status: ok` + `result`) are unchanged.

Direct in-process construction of `FinancialInput` / `FinancialModel` still raises Pydantic `ValidationError`. The structured codes apply to `run_function` and HTTP calculation responses.

## Versioning

Public routes are under `/v1/`. Breaking contract changes require an explicit versioning decision and documentation update.
