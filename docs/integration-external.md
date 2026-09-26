# External annual integration (I2)

How a separate client (e.g. a future Next.js mock on `localhost:3000`) calls this
Financial Engine without knowing Dairy / Agriculture / Core internals.

## Run the engine

```bash
python run_server.py
```

Base URL: `http://127.0.0.1:8000`  
OpenAPI: `http://127.0.0.1:8000/docs`

Local reload alternative: `python -m uvicorn api.app:app --reload`

## Canonical annual call

```http
POST /v1/functions/pl.summary/run
Content-Type: application/json
```

Body: flat JSON numbers (Phase 1 Dairy Operating Statement drivers).

### Required

- `milking_cows`
- `litres_per_cow`
- `milk_price`

### Optional (omit → treated as `0`)

- Schemes: `biss`, `acres`, `other_grants`
- Other income: `cattle_sales`, `land_leasing_income`, `other`
- Operating costs: `feed`, `fertiliser`, `vet`, `contractor`, `labour`, `insurance`, `fuel`, `electricity`, `water`, `repairs_maintenance`, `rent_lease`, `professional_fees`, `levies`, `other_operating_costs`
- Finance: `loan_repayments` (does **not** reduce Operating Surplus)

Unknown field names, `null`, negatives, and non-numbers are rejected.

### Example (approved sample farm)

```json
{
  "milking_cows": 100,
  "litres_per_cow": 5000,
  "milk_price": 0.40,
  "biss": 20000,
  "acres": 5000,
  "other_grants": 0,
  "cattle_sales": 15000,
  "land_leasing_income": 0,
  "other": 0,
  "feed": 80000,
  "fertiliser": 15000,
  "vet": 5000,
  "contractor": 10000,
  "labour": 40000,
  "insurance": 4000,
  "fuel": 6000,
  "electricity": 3000,
  "water": 0,
  "repairs_maintenance": 0,
  "rent_lease": 0,
  "professional_fees": 0,
  "levies": 0,
  "other_operating_costs": 0,
  "loan_repayments": 12000
}
```

## Success response

HTTP **200**. Envelope:

```json
{
  "status": "ok",
  "function": "pl.summary",
  "result": { }
}
```

| Display need | Read from |
|--------------|-----------|
| Currency | `result.currency` (`EUR`) |
| Period | `result.period` (`annual`) |
| Milk revenue | `result.revenue.milk` |
| Scheme revenue | `result.revenue.schemes` |
| Other revenue | `result.revenue.other` |
| Operating income total | `result.revenue.total` |
| Cost lines | `result.costs.lines.*` |
| Operating costs total | `result.costs.total` |
| Operating Surplus | `result.profit.net` |
| Margin (0–1) | `result.profit.margin` |
| Margin % | `result.profit.margin_pct` |
| Loan repayments | `result.finance.loan_repayments` |

Approved reference totals: income **240000**, schemes **25000**, costs **163000**, Operating Surplus **77000**, margin **0.3208** / **32.08%**, loans **12000**.

Treat published aggregate `total` fields as authoritative (do not re-sum rounded lines for truth).

## Error / incomplete responses

**Always branch on body `status` and `error.code`.** Do not parse `message` text.

Most validation outcomes use HTTP **200** with an application status:

| Situation | HTTP | `status` | Branch |
|-----------|------|----------|--------|
| Missing required field | 200 | `needs_input` | `error.code` = `missing_required`, `missing[].field` (+ `unit`) |
| Unknown / null / negative / wrong type | 200 | `error` | `error.code` (e.g. `unknown_field`) |
| Unknown calculation ID | **404** | `error` | `error.code` = `unknown_calculation` |

### `needs_input` example

```json
{
  "status": "needs_input",
  "function": "pl.summary",
  "missing": [{"field": "milk_price", "unit": "EUR/litre"}],
  "provided": ["litres_per_cow", "milking_cows"],
  "error": {
    "code": "missing_required",
    "message": "milk_price is required",
    "field": "milk_price"
  }
}
```

### `error` example (unknown field)

```json
{
  "status": "error",
  "function": "pl.summary",
  "error": {
    "code": "unknown_field",
    "message": "...",
    "field": "random_field"
  }
}
```

## CORS (local Next.js)

Browser apps on another origin need CORS. Application layer only (`api/app.py`).

- Default allowlist: `http://localhost:3000`
- Override: `CORS_ALLOW_ORIGINS` comma-separated list (e.g. `http://localhost:3000,http://127.0.0.1:3000`)

Engine: `127.0.0.1:8000`. Mock UI: typically `localhost:3000`.

## Client must not

- Recalculate milk revenue, cost totals, or Operating Surplus in the frontend
- Call Dairy / Agriculture / Core Python packages
- Assume HTTP endpoints for simulation, scenarios, provenance, or field-metadata catalogues (deferred)

## Platform-owned (not this engine)

Loan product cards, supplier debt lists, financial event calendars, Jan–Dec chart series (mock/Platform data for now).

## Discovery (optional)

`GET /v1/functions` returns calculation `key`, `description`, `required`, `optional` **names** — not units. Units appear on `needs_input.missing[].unit`.

Full public contract: [`api-contract.md`](api-contract.md).
