# API Contract

Canonical description of the Financial Service HTTP calculation contract.
Implementation: `farm_functions/registry.py` (authoritative catalogue), `farm_functions/runner.py`, `farm_functions/schemas.py`, `api/app.py` (composition root), `api/routes.py` (HTTP handlers).

For a separate frontend (e.g. Next.js mock) integrating the annual Operating Statement over HTTP, start with [`integration-external.md`](integration-external.md) (I2: request/response map, error branching, CORS).

Domain types (`FinancialModel` → `FinancialInput` → calculations → `FinancialResult`) live in `farm_functions/domain.py`. They do **not** change this HTTP contract: request bodies remain a flat JSON object of numbers; statuses remain `ok` / `needs_input` / `error`.

Annual P&L provenance (`explain_annual_pnl`) is in-process only. It is not included in HTTP calculation responses.

## Contract snapshot

**Service:** Stateless annual dairy P&L calculator (validate inputs, run named calculations, return structured results).

**Calculations (8 public IDs):** `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`, `pl.summary` — from `CALCULATION_CATALOGUE` only.

**Inputs:** Flat JSON numbers per calculation. Required fields → `needs_input` when omitted. Optional omitted → `0`. Explicit `0` is valid. Unknown fields / null / negatives / wrong types → `error` with stable codes. Units come from `FIELD_UNITS` / `needs_input` / metadata — **not** from discovery.

**Outputs:** Money calculations → `{amount, currency:"EUR"}`. `profit.margin` → margin object. `pl.summary` / in-process `FinancialResult` → `{currency, period, revenue, costs, profit, finance}` with `period:"annual"`.

**Canonical annual view (ADR-0009):** `pl.summary` is the Phase 1 **canonical annual Operating Statement**. Atomic catalogue IDs remain supporting schedules and must reconcile to `pl.summary` for the same inputs (published aggregates authoritative per ADR-0005). In-process `calculate_annual_pnl` wraps the same composition.

**Phase 1 financial meaning (ADR-0007; naming Option A, ADR-0009):** Public IDs `profit.net` / `profit.margin` are kept for API compatibility; their meaning is **Operating Surplus** / Operating Surplus margin (operating income − operating costs). `costs.total` and `costs.lines` are **operating costs only**. `loan_repayments` is reported under `finance` and does **not** reduce Operating Surplus. This is not full accounting net profit.

**Validation:** Codes `missing_required`, `unknown_field`, `null_not_allowed`, `negative_value`, `invalid_type`, `non_finite_value`, `unknown_calculation`. Branch on `error.code`, not message text.

**Phase 1 validation principles (ADR-0008):** Validation checks whether inputs are **structurally usable** for the calculation (finite ≥ 0, presence, types). It does **not** judge whether farm numbers are normal, efficient, or commercially good. Financial inputs are **independent** except where a field is required to run a named calculation (e.g. milk trio for `revenue.milk`). No Phase 1 **maximums**. No calculation-engine warning / advisory / benchmark channel. Unusual-but-valid values (e.g. high contractor cost, `milk_price = 0`, zero cows with positive litres) remain `ok`.

**Precision:** Internal `float` (ADR-0006); publish with banker's rounding (ADR-0005); published aggregate totals are authoritative; rounded lines need not re-sum exactly; provenance stays unrounded.

**Provenance (ADR-0010):** In-process `explain_annual_pnl` for the seven catalogue entries with `supports_provenance=True`. `pl.summary` has no separate provenance object — explain it via those seven component records plus `finance` from the statement result. Human labels for `profit.net` / `profit.margin` come from catalogue / ADR-0007 (Operating Surplus / margin). Provenance stays unrounded; published aggregates remain authoritative. **Not on HTTP** (no Phase 1 `/explain` endpoint). Natural-language explanation belongs to a future agent/platform layer.

**Simulation (ADR-0011):** In-process `simulate_annual_pnl` — explicit overrides on a copy of `FinancialInput`, then canonical `calculate_annual_pnl` for base and simulated results. No second formulas, no engine-side deltas, no forecasting. **Not on HTTP** in Phase 1.

**Scenarios (ADR-0012):** In-process `run_scenario` / `run_scenarios` — caller-defined name + overrides executed through B7. Independent runs from the same base; no ranking, deltas, Base/Best/Worst semantics, or persistence. **Not on HTTP** in Phase 1.

**Out of scope here:** persistence, authentication, forecasting, monthly cashflow, KPIs, multi-currency, multi-period, AI-generated calculations, Supabase/farm CRUD.

### Intentional interface differences

| Layer | Representation |
|-------|----------------|
| HTTP / runner | Flat per-calculation field dict |
| Domain | `FinancialModel` envelope (`period`, `currency`, `inputs: FinancialInput`) for in-process annual P&L only |
| Discovery | `key`, `description`, `required`, `optional` — no units (by design) |
| Provenance | Unrounded formula values via `explain_annual_pnl`; not on HTTP; `pl.summary` explained by components + `finance` (ADR-0010) |
| Simulation | In-process `simulate_annual_pnl` only (ADR-0011); not on HTTP |
| Scenarios | In-process named packages via B7 (ADR-0012); not on HTTP |

Do **not** force HTTP to accept `FinancialModel`, and do not treat discovery as a full unit dictionary.

## Phase 1 public surface (freeze)

This section freezes what App Platform integrations may depend on after Workstream B (B1–B8). It invents no new behaviour.

### HTTP calculation surface

Supported endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/livez`, `/health` | Liveness |
| `GET` | `/v1/functions` | Discovery (`key`, `description`, `required`, `optional`) |
| `POST` | `/v1/functions/<calculation_id>/run` | Run one registered calculation |
| `POST` | `/v1/demo/pl-summary` | Demo: `pl.summary` on sample farm |

**Eight registered calculation IDs** (`CALCULATION_CATALOGUE` only):

`revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`, `pl.summary`

HTTP request/response envelopes use statuses `ok` / `needs_input` / `error`. On failure, branch on structured `error.code` (see Validation above), not message text.

### In-process Python surface

Package exports (`farm_functions`):

| Symbol | Role | On HTTP? |
|--------|------|----------|
| `run_function` / `list_functions` / `list_input_metadata` | Same catalogue as HTTP | HTTP uses these internally |
| `calculate_annual_pnl` | Canonical annual `FinancialResult` from `FinancialModel` | No — in-process only |
| `explain_annual_pnl` | Deterministic calculation provenance (ADR-0010) | No — in-process only |
| `simulate_annual_pnl` | Explicit input-override simulation (ADR-0011) | No — in-process only |
| `run_scenario` / `run_scenarios` | Named scenario packages via B7 (ADR-0012) | No — in-process only |
| `FinancialInput` / `FinancialModel` / `FinancialResult` | Typed annual P&L domain | No — not the HTTP body shape |
| `SimulationRequest` / `SimulationResult` | B7 contracts | No |
| `ScenarioDefinition` / `ScenarioResult` / `ScenarioBundle` | B8 contracts | No |
| `CalculationProvenance` | Provenance record type | No |

Phase 1 does **not** expose HTTP endpoints for provenance, simulation, or scenarios.

### Stable IDs and financial labels

- Calculation **IDs** are stable technical identifiers (including `profit.net` and `profit.margin`).
- Human-readable financial **labels** come from the catalogue `description` on each `CALCULATION_CATALOGUE` entry (also returned by discovery as `description`). That is the authoritative label source — do not invent a second label dictionary.
- Phase 1 meaning: `profit.net` = **Operating Surplus**; `profit.margin` = **Operating Surplus Margin** (ADR-0007). These IDs are not full accounting net profit.

### Error boundary (intentional)

| Path | How failures appear |
|------|---------------------|
| HTTP / `run_function` | Structured envelope: `needs_input` or `error` with stable `error.code` |
| In-process domain (`FinancialInput` / `FinancialModel`), simulation, scenarios | Python exceptions: typically Pydantic `ValidationError` and/or plain `ValueError` (e.g. unknown override field, blank scenario name) |

This split is **intentional** for Phase 1. There is no unified structured-error framework for in-process B7/B8 calls. A future HTTP exposure of simulation/scenarios may introduce an adapter; that is out of this freeze.

### Sample farm JSON vs flat drivers

Demo sample [`sample_data/farm.json`](../sample_data/farm.json) is **nested** (`revenue` / `costs` / `finance`). The loader flattens it:

```text
nested sample JSON
→ farm_functions.loaders.json_loader.farm_to_inputs / load_sample_inputs
→ flat FinancialInput / runner field dict
```

HTTP calculation bodies and `FinancialInput` use the **flat** field set. The sample is not restructured; the loader is the bridge.

## Current Financial Domain Contract Scope

**Active development branch:** `financial-engine` (Workstream B). Phase 1 Operating Surplus semantics are defined in ADR-0007.

### Included

- Deterministic annual dairy P&L calculation service
- Eight stable public calculation IDs via `CALCULATION_CATALOGUE`
- Typed in-process domain (`FinancialInput` / `FinancialModel` / `FinancialResult` / `calculate_annual_pnl`)
- Phase 1 Operating Surplus model: operating income, extensible operating-cost catalogue, separate finance (`loan_repayments`)
- `pl.summary` as the canonical annual Operating Statement (ADR-0009); atomic IDs as reconciling schedules
- Phase 1 structural validation and input independence (ADR-0008): no advisory maxima or cross-field farm rules
- Strict input validation, units metadata, structured errors
- In-process provenance for seven calculations with documented explainability assembly (ADR-0010)
- In-process annual input-override simulation (ADR-0011)
- In-process caller-defined named scenarios via B7 (ADR-0012); ephemeral; not persisted here
- Public HTTP discovery and execution (`/v1/functions`, `/run`, demo)
- Reconciliation, golden/reference, error, precision, and alignment regression tests
- Publication rounding (ADR-0005), Phase 1 float precision (ADR-0006), Operating Surplus (ADR-0007), validation independence (ADR-0008), canonical Operating Statement (ADR-0009), provenance boundary (ADR-0010), simulation (ADR-0011), scenarios (ADR-0012)

### Not included (do not assume)

- Principal vs interest split for `loan_repayments`
- Full accounting net profit (depreciation, tax, drawings, livestock valuation, etc.)
- Advisory validation, farm benchmarking, anomaly detection, KPIs, normal ranges, soft warnings
- Scenarios as persisted libraries / Base–Best–Worst engine types / sensitivity / forecasting (in-process named packages exist via ADR-0012; persistence and judgement stay elsewhere)
- Monthly cash flow, balance sheet, KPIs, valuation, optimisation
- Persistence, database, authentication, farm identity
- Accounting / banking / CRM integrations
- Multi-currency, multi-period
- HTTP simulation / scenario / provenance endpoints or HTTP `FinancialModel` as the request body
- AI-generated financial calculations / broader platform orchestration

## Calculation identifiers

Each calculation has a **stable public ID** (example: `revenue.milk`). These IDs are defined explicitly in `CALCULATION_CATALOGUE` in `farm_functions/registry.py`.

- Integrations MUST call calculations by this ID (`POST /v1/functions/<calculation_id>/run` and the `function` field in responses).
- Discovery (`GET /v1/functions`) exposes the same IDs in the `key` field.
- Internal Python handler, module, or class names are implementation details and may change independently of the public ID.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/livez` | Liveness (process up; cheap) |
| `GET` | `/health` | Liveness alias (same body as `/livez`) |
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
