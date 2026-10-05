# External integration (I2 annual + P1.4 monthly)

How a separate client (e.g. a Next.js mock on `localhost:3000`) calls this
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

## Canonical monthly call (P1.4)

```http
POST /v1/functions/pl.monthly/run
Content-Type: application/json
```

Body: flat JSON — period identity plus monthly financial drivers. The client must
**not** construct Domain types (`MonthlyDairyStatementModel`, etc.).

### Required

- `year` (calendar year ≥ 1)
- `month` (1–12)
- `milk_litres`
- `milk_price`

### Optional (omit → treated as `0`)

- Schemes: `biss`, `acres`, `other_grants` (EUR for the statement month)
- Other income: `cattle_sales`, `land_leasing_income`, `other`
- Operating costs: `feed`, `fertiliser`, `vet`, `contractor`, `labour`, `insurance`, `fuel`, `electricity`, `water`, `repairs_maintenance`, `rent_lease`, `professional_fees`, `levies`, `other_operating_costs`
- Finance: `loan_repayments` (does **not** reduce Operating Surplus)

Unknown field names (including annual-only `milking_cows` / `litres_per_cow`), `null`,
negatives, wrong types, and invalid months are rejected. Monthly is **not** annual ÷ 12.

### Example (approved March 2026 reference)

```json
{
  "year": 2026,
  "month": 3,
  "milk_litres": 40000,
  "milk_price": 0.40,
  "biss": 2000,
  "acres": 500,
  "other_grants": 0,
  "cattle_sales": 1000,
  "land_leasing_income": 0,
  "other": 0,
  "feed": 5000,
  "fertiliser": 1000,
  "loan_repayments": 1500
}
```

### Success shape

Same envelope as annual (`status` / `function` / `result`). Differences:

| Field | Monthly |
|-------|---------|
| `function` | `pl.monthly` |
| `result.period` | `{ "kind": "month", "year": 2026, "month": 3 }` (object, not `"annual"`) |
| Money nests | Same: `revenue` / `costs` / `profit` / `finance` |

Approved reference: milk **16000**, schemes **2500**, other **1000**, income **19500**,
costs **6000**, Operating Surplus **13500**, margin **0.6923** / **69.23%**, loans **1500**.

Error branching is identical to annual (`needs_input` / `error.code`). CORS is unchanged.

## Multi-period call (ADR-0021 / P2.4 — live)

Public ID **`pl.months`**. Nested request over Domain multi-month + optional YTD.

```http
POST /v1/functions/pl.months/run
Content-Type: application/json
```

### Request

Nested body (exception to flat annual/monthly payloads):

| Field | Rule |
|-------|------|
| `months` | **Required** non-empty array. Each item = same fields as `pl.monthly` (`year`, `month`, `milk_litres`, `milk_price`, optional drivers omit → `0`). |
| `ytd` | **Optional**. Object `{ "year", "as_of_month" }` to request YTD; omit or `null` for months-only. |

```json
{
  "months": [
    {
      "year": 2026,
      "month": 1,
      "milk_litres": 100,
      "milk_price": 1.0,
      "feed": 10,
      "loan_repayments": 5
    },
    {
      "year": 2026,
      "month": 2,
      "milk_litres": 1000,
      "milk_price": 1.0,
      "feed": 900,
      "loan_repayments": 10
    }
  ],
  "ytd": {
    "year": 2026,
    "as_of_month": 2
  }
}
```

Do **not** send chart coordinates, forecast values, UI labels, farm IDs, or
colours. Sparse / cross-year month lists are allowed when `ytd` is omitted.
Named YTD requires contiguous January…`as_of_month` for that year (Domain
rules); months after `as_of_month` are ignored for YTD.

### Success shape

```json
{
  "status": "ok",
  "function": "pl.months",
  "result": {
    "currency": "EUR",
    "months": [
      {
        "currency": "EUR",
        "period": { "kind": "month", "year": 2026, "month": 1 },
        "revenue": { "milk": 100.0, "schemes": 0.0, "other": 0.0, "total": 100.0 },
        "costs": { "lines": { "feed": 10.0 }, "total": 10.0 },
        "profit": { "net": 90.0, "margin": 0.9, "margin_pct": 90.0 },
        "finance": { "loan_repayments": 5.0 }
      }
    ],
    "ytd": {
      "currency": "EUR",
      "period": {
        "kind": "ytd",
        "year": 2026,
        "as_of_month": 2,
        "months_included": [1, 2]
      },
      "revenue": { "milk": 1100.0, "schemes": 0.0, "other": 0.0, "total": 1100.0 },
      "costs": { "lines": { "feed": 910.0 }, "total": 910.0 },
      "profit": { "net": 190.0, "margin": 0.1727, "margin_pct": 17.27 },
      "finance": { "loan_repayments": 15.0 }
    }
  }
}
```

When `ytd` is omitted or JSON `null` on the request, `result.ytd` is **`null`**
(key always present).

- `result.months` — chronological monthly Operating Statements (Domain dumps).
- Jan–Dec chart: read `period.month`, `revenue.total`, `costs.total`, `profit.net`
  from each monthly result. Engine does not return chart DTOs.

### Errors

Same envelope vocabulary. Missing top-level `months` → `needs_input` /
`missing_required`. Nested missing drivers, duplicates, YTD gaps → `error` with
existing codes; period-set structure uses `details.reason` (`duplicate_period`,
`ytd_incomplete`, `ytd_year_mismatch`, `empty_months`). Nested missing fields are
**not** `needs_input` (runner only scans top-level keys). Branch on `error.code`
(+ `details.reason`), not message text.

Discovery: `required: ["months"]`, `optional: ["ytd"]` — nested month field names
are documented here, not listed in discovery.

`pl.summary` and `pl.monthly` remain unchanged.

## CORS (local Next.js)

Browser apps on another origin need CORS. Application layer only (`api/app.py`).

- Default allowlist: `http://localhost:3000`
- Override: `CORS_ALLOW_ORIGINS` comma-separated list (e.g. `http://localhost:3000,http://127.0.0.1:3000`)

Engine: `127.0.0.1:8000`. Mock UI: typically `localhost:3000`.

## Client must not

- Recalculate milk revenue, cost totals, Operating Surplus, loan balances / instalments, or % repaid in the frontend
- Call Dairy / Agriculture / Core Python packages
- Assume HTTP endpoints for simulation, scenarios, provenance, or field-metadata catalogues (deferred)

## Platform-owned (not this engine)

Loan product data (lender, purpose, rate type), supplier debt lists, financial
event calendars, forecast UI and chrome. Jan–Dec **actual** chart series and YTD
OS cards call `pl.months`; cash balance cards call `cf.months`.

Engine-owned maths (ADR-0025): loan cards call `loan.schedule` with the loan's
current `balance`, `annual_rate` (0–1), `remaining_months` and next instalment
`year` / `month` (+ `original_principal` for % repaid). Pass each month's
`interest` / `principal` into `cf.*` as `interest_paid` /
`loan_principal_repayments`. Projected-month maths will also come from the Engine.

## Discovery (optional)

`GET /v1/functions` returns calculation `key`, `description`, `required`, `optional` **names** — not units. Units appear on `needs_input.missing[].unit`.

Full public contract: [`api-contract.md`](api-contract.md).
