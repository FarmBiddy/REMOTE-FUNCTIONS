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

## Service token (ADR-0049)

When the engine has `ENGINE_API_KEY` set, every `/v1/...` call sends
`Authorization: Bearer <key>` (401 `unauthorized` otherwise). Call the engine
from the Platform **backend** only, after checking the user's login; never put
the key in browser code.

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

Engine-owned maths (ADR-0025): the loans card calls `loan.schedule` once with
`loans[]`, each with its current `balance`, `annual_rate` (0–1),
`remaining_months` and next instalment `year` / `month` (+ `original_principal`
for % repaid). Use `total_balance` / `total_monthly_payment` for the card header
(never sum in the UI). Pass the combined `months[]` `interest` / `principal` into
`cf.*` as `interest_paid` / `loan_principal_repayments`.

Family living money taken from the farm account goes in `household_drawings`
(cash only, financing outflow; recurs in `cf.forecast`; ADR-0030).

Projected months (ADR-0026): call `pl.forecast` / `cf.forecast` with the actual
months (incl. the same months last year) and the months to project, adding any
known values (co-op price, scheme payments, `loan.schedule` rows). Chart the
returned `statement`s; for the cash balance send actual + projected `inputs` to
`cf.months`. Show `run_rate` to explain the projection.

KPI tiles (ADR-0028): call `kpi.summary` with the same months as the chart
(actual, or actual + projected `inputs`) and the average `milking_cows`. Use
`per_litre_c` for c/L cards, `per_cow` for herd cards and `dscr` for "Can I pay
my loans?". `null` means not computable (no litres / cows / repayments).
Thresholds (e.g. a lender's minimum DSCR) are Platform / Biddy policy.
Optional: `milk_solids_kg` (co-op statements) → `per_kg_ms`; `hectares` →
`per_hectare`; `debt_balance` (`loan.schedule` `total_balance`) → `debt` per cow / ha
(ADR-0032).
Variable / fixed costs and gross margin (revenue − variable costs) follow the
Teagasc split (ADR-0033).

Machinery and buildings (ADR-0037): keep the register on the Platform and call
`assets.schedule` for the period to get depreciation and net book values (results
in input order). Land is not depreciated.

Milk quality (ADR-0052): send the co-op's monthly statement figures to
`milk.quality` (SCC / TBC in thousands per ml). The four cards read
`period.scc_k`, `period.tbc_k`, `period.fat_pct`, `period.protein_pct` and compare
with the **average** you supply (SCC: ICBF weekly milk recording by province; fat /
protein: CSO national monthly, AKM01). Because these are seasonal, prefer
`benchmarks.<metric>.monthly_average: [{year, month, value}]` covering every
statement month: the engine weights it by the farm's own litres for a
like-for-like average (`average_basis: litre_weighted_monthly`). A single
`average` still works (`fixed`). Show
`vs_benchmarks.<metric>.position` (above / below / about) and
`better_than_average` (null when about) — no maths in the UI. `best20` (ICBF best
20%) and `top10` are optional extra references. The engine stays offline and
stores no benchmarks. Send the co-op price schedule as `pricing` to show the
milk-price breakdown and `value.gain_to_average_eur` ("€ a year if your fat and
protein reached the average"). Pass `period.milk_solids_kg` to `kpi.summary` for the
kg MS KPIs.

Net profit (ADR-0038): call `pl.net` with the period's months, `depreciation`
(`assets.schedule` `total.depreciation`), `interest` (the period's `loan.schedule`
interest) and the livestock / stock valuations at start and end.

Multi-year plan (ADR-0042): call `plan.projection` with the last 12 actual
months, the current bank balance, cows, loans, the asset register and any
investment. Assumptions are per-year lists the Platform prefills from market
data or the advisor (presets: cautious / base / optimistic) and the user edits;
send nothing for "everything stays as this year". Show `assumptions_used`
next to the figures, and `flags` for years with negative cash or DSCR below the
lender's `min_cover`.

Reports (ADR-0041): build one farm file and call `report.bank`,
`report.advisor` or `report.accountant`. Each returns structured sections
(outputs of the matching IDs) for the Platform to render as a PDF or screen.
`drawings` / `tax` / `off_farm_income` are totals for the reporting period.

Balance sheet (ADR-0039): call `bs.summary` for a month end with the bank
balance (`cash`, negative = overdraft), debtors, stock, livestock and land values,
creditors (supplier debt card), the same `loans[]` as `loan.schedule` and the
same register as `assets.schedule`. The Engine splits loans and values assets.

"How much can I borrow?" (ADR-0036): call `debt.capacity` with 12 months
(actual or projected), the household `drawings`, `tax`, `off_farm_income`, and
the loan's `annual_rate`, `term_months` and the lender's `min_cover` (e.g. 1.25).
Show `new_loan.max_principal` and `repayment_cover`.

Variance (ADR-0035): "vs last year" / "vs budget" columns call `pl.compare` or
`cf.compare` with the two sets of months. Show `milk.volume_effect` /
`milk.price_effect` to explain a milk income change. Colour (cost up = bad) is
Platform presentation.

Send `shocks_from_year` / `shocks_from_month` = the first projected month so
scenarios mean "from now on" and past months stay as they happened (ADR-0040).

"Is this change worth it?" (ADR-0045): `decision.partial_budget` with the
farmer's or advisor's labelled annual amounts (rent land, contract rearing, buy
vs grow feed). Labels are yours and come back unchanged.

"Is it a good investment over its life?" (ADR-0046): `decision.investment`
with the outlay, the yearly benefit (or year-by-year cash flows), any resale
value and the discount rate the user or lender chooses. Show NPV and IRR with
the discounted payback; pair with `risk.sensitivity` for affordability.

"What affects me most?" (ADR-0044): call `risk.tornado` with the same months
as the what-if panel and draw `drivers` as a tornado chart (bars from `low` to
`high`, already sorted). `rank_by: closing_cash` for a cash view.

Interest rates and stress tests (ADR-0043): mark variable-rate loans with
`variable: true`. Send the same `loans` to `risk.sensitivity` and use
`rate_shift_pp` per scenario, or `interest_rate_shift_pp` per year in
`plan.projection`. Stress tests are your named presets of combined shocks
(e.g. "2016": milk_price_c −9, lines_pct.feed +20, rate_shift_pp +2).

What-if panel (ADR-0029): call `risk.sensitivity` with the chart's P&L months,
the cash months, `opening_cash` and the scenarios the farmer picks (e.g.
`{"name": "milk -5c", "milk_price_c": -5}`). Show each scenario's
`break_even.cash_milk_price_c` as "below X c/L you go overdrawn" and
`surplus_milk_price_c` as "below X c/L you make a loss". A cash break-even above
`milk_price_c` means that scenario already goes overdrawn (see `lowest_cash`).

"Can I afford it?" (ADR-0031): add `investments` to a scenario, e.g.
`{"name": "new parlour", "investments": [{"year": 2026, "month": 11, "amount": 120000,
"loan": {"amount": 100000, "annual_rate": 0.05, "remaining_months": 120},
"monthly_effects": {"labour": -1500}}]}`, and compare it with `base`: DSCR,
lowest cash, overdraft months, break-evens and `simple_payback_months`.

Herd size / derogation (ADR-0033): `{"name": "10% fewer cows", "herd_pct": -10}`
moves litres, variable costs and cattle sales; fixed costs stay.

## Discovery (optional)

`GET /v1/functions` returns calculation `key`, `description`, `required`, `optional` names.
`GET /v1/functions/{id}` adds `units` (every field, nested ones included) and
`input_schema` (JSON Schema: types, nested item shapes, required, defaults,
choices) so forms and Biddy questions can be generated instead of hand-coded.
The same units appear on `needs_input.missing[].unit` (ADR-0048).

Every response carries `meta.engine_version`; month lists are capped at 120 items.
The Operating Surplus is `operating_surplus` in all post-Phase-1 outputs
(`profit.net` in `pl.*`). See "Conventions" in the API contract.

Generate client types from the engine instead of writing them by hand (ADR-0051):
`npx openapi-typescript http://127.0.0.1:8000/openapi.json -o lib/financial-engine/engine.d.ts`.
Each run route's response is `<Id>Response` (`<Id>Ok` | `NeedsInputEnvelope` | `ErrorEnvelope`).

Full public contract: [`api-contract.md`](api-contract.md).
