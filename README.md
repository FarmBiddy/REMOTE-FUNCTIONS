# Farm cost and revenue functions

Small calculation library extracted from the Dairy Financials prototype. It covers a **Phase 1 annual operating P&L**: operating income, operating costs, **Operating Surplus**, and separately reported debt service (`finance.loan_repayments`). Public calculation ID `profit.net` means Operating Surplus (ADR-0007) — not full accounting net profit.

Functions take explicit numbers. They do not read a database. A sample JSON is used now so the formulas can be checked; a platform loader can replace that later.

## Contract

Every call returns one of:

```json
{ "status": "ok", "function": "revenue.milk", "result": { "amount": 200000, "currency": "EUR" } }
```

```json
{
  "status": "needs_input",
  "function": "revenue.milk",
  "missing": [{ "field": "milk_price", "unit": "EUR/litre" }],
  "provided": ["milking_cows", "litres_per_cow"]
}
```

Missing inputs are listed with field name and unit (plus `path`, e.g. `months[3].milk_price`, when nested; ADR-0027). They are never guessed. Extra / unknown fields are rejected (`error`). Explicit `0` is valid; `null` and negatives are invalid. Full contract: [`docs/api-contract.md`](docs/api-contract.md).

**Phase 1 public surface (freeze):** HTTP exposes the eight calculation IDs above. In-process-only capabilities — `calculate_annual_pnl`, `explain_annual_pnl` — are documented in [`docs/api-contract.md`](docs/api-contract.md) (Phase 1 public surface). Catalogue `description` is the human-readable label source (`profit.net` = Operating Surplus). HTTP/runner failures use structured `error.code`; in-process domain calls may raise Pydantic/`ValueError` (intentional Phase 1 split).

Units: **EUR**, **annual**. `profit.margin` returns a 0–1 `margin` and a `margin_pct`. Published money and margins use **banker's rounding** (round half to even; ADR-0005).

## Functions

Keys in this table are **stable public calculation IDs** (not Python function names). Integrations must use these IDs. Catalogue: `farm_functions/registry.py`.

| Calculation ID | Required inputs | Formula |
|----------------|-----------------|---------|
| `revenue.milk` | `milking_cows`, `litres_per_cow`, `milk_price` | cows × litres sold/paid × price |
| `revenue.schemes` | — | BISS + ACRES + other operating grants |
| `revenue.other` | — | cattle sales + land leasing income + other operating income |
| `revenue.total` | milk fields | milk + schemes + other (operating income) |
| `costs.total` | — | sum of operating cost lines (missing = 0; excludes loans) |
| `profit.net` | `revenue`, `costs` | Operating Surplus = revenue − operating costs |
| `profit.margin` | `revenue`, `costs` | Operating Surplus / revenue |
| `pl.summary` | milk fields | **canonical** annual Operating Statement + `finance.loan_repayments` |
| `pl.monthly` | `year`, `month`, `milk_litres`, `milk_price` | Explicit monthly Operating Statement (not annual ÷ 12) + `finance.loan_repayments` |
| `pl.months` | `months[]` (+ optional `ytd`) | Multi-month OS list + optional YTD (ADR-0021; not annual ÷ 12) |
| `cf.monthly` | `year`, `month` (+ optional `opening_cash`) | Explicit monthly Cash Flow: operating / investing / financing, cash in/out, net; closing cash when opening given (ADR-0022/0023/0024) |
| `cf.months` | `opening_cash`, `months[]` | Consecutive months rolled forward: each month opens with the previous closing cash; period totals + closing cash (ADR-0024) |
| `loan.schedule` | `loans[]` (each `balance`, `annual_rate`, `remaining_months`, `year`, `month`, optional `original_principal`) | Per-loan amortisation from today's state (equal instalments, interest / principal, % repaid) + portfolio totals and combined monthly debt service (feeds `cf.*` `interest_paid` / `loan_principal_repayments`) (ADR-0025) |
| `assets.schedule` | `assets[]`, `from_year`, `from_month`, `to_year`, `to_month` | Fixed asset register: straight-line or reducing-balance depreciation; opening NBV + additions − depreciation = closing NBV per asset, category and total (ADR-0037) |
| `debt.capacity` | `months[]`, `annual_rate`, `term_months` (+ optional `drawings`, `tax`, `off_farm_income`, `min_cover`) | Repayment capacity (surplus + off-farm − drawings − tax), cover of current debt service, and the largest affordable new loan (ADR-0036) |
| `kpi.summary` | `months[]`, `milking_cows` (+ optional `milk_solids_kg`, `hectares`, `debt_balance`) | Dairy KPIs over the months sent: c/L (incl. each cost line, variable / fixed, gross margin), per cow, per kg milk solids, per hectare, debt per cow / ha; DSCR = Operating Surplus / loan repayments; undefined ratios `null` (ADR-0028, ADR-0032) |
| `pl.net` | `months[]` (+ optional `depreciation`, `interest`, livestock / stock opening and closing values) | Net profit before tax: Operating Surplus ± valuation changes − depreciation − interest, with EBIT and net margin (ADR-0038) |
| `bs.summary` | `year`, `month` (+ balances, `loans[]`, `assets[]`) | Balance sheet at month end: loans split within / after 12 months, fixed assets at NBV, net worth, equity %, debt-to-assets %, current ratio, working capital (ADR-0039) |
| `pl.compare` | `actual[]`, `comparison[]` | P&L variance vs prior year or budget: every line with change and %, margin change in points, milk change split into volume and price effects (ADR-0035) |
| `cf.compare` | `actual[]`, `comparison[]` | Cash flow variance vs prior year or budget: every line, section and total (movements only) (ADR-0035) |
| `risk.sensitivity` | `pl_months[]`, `cf_months[]`, `opening_cash` (+ `scenarios[]`) | What-if scenarios (milk c/L, volume %, herd size %, % per line): surplus, DSCR, closing / lowest cash, overdraft months; investments with optional loan and monthly effects ("Can I afford it?", payback); exact milk-price break-evens per scenario (ADR-0029, ADR-0031) |
| `risk.tornado` | `pl_months[]`, `cf_months[]`, `opening_cash` (+ `loans`, `step_pct`, `rank_by`) | Driver ranking: milk price, volume, herd, each line with an amount and variable interest rates moved one at a time ±step, sorted by swing (ADR-0044) |
| `decision.partial_budget` | labelled annual `added_income`, `reduced_costs`, `added_costs`, `reduced_income` (+ optional `capital`) | Partial budget for a farm change: net annual effect, capital charge, payback and ROI; enterprise-independent (ADR-0045) |
| `decision.investment` | `amount`, `discount_rate`, `annual_benefit` + `life_years` or `cash_flows[]` (+ `residual_value`) | Investment appraisal: NPV, IRR, simple and discounted payback, profitability index, discounted schedule (ADR-0046) |
| `report.bank` / `report.advisor` / `report.accountant` | farm file (`pl_months[]`, `cf_months[]`, `opening_cash`, `milking_cows` + optional loans, assets, valuations, projections, prior year) | Report bundles composed from the other IDs: bank (profit, DSCR, capacity, balance sheet, cash outlook), advisor (KPIs, vs last year, what-ifs), accountant (P&L, net profit, fixed assets, balance sheet, cash flow) (ADR-0041) |
| `plan.projection` | `base_pl_months[]` (12), `opening_cash`, `milking_cows` (+ optional per-year assumptions, loans, assets, investments, land, livestock, `min_cover`) | Multi-year annual projection (1–10 years): P&L, net profit, cash, debt and DSCR, balance sheet, KPIs and flags per year (ADR-0042) |
| `pl.forecast` | `history[]`, `forecast[]` | Projected monthly Operating Statements: same month last year × YTD run-rate per line; milk price carries the latest actual; known values override (ADR-0026) |
| `cf.forecast` | `history[]`, `forecast[]` | Projected monthly Cash Flows: operating lines seasonal × run-rate; investing / financing only when given (e.g. `loan.schedule` rows); `inputs` plug into `cf.months` (ADR-0026) |

`pl.summary` is the Phase 1 canonical annual Operating Statement (ADR-0009). `pl.monthly` is the explicit monthly statement (ADR-0019). `pl.months` returns chronological monthly statements and optional YTD (ADR-0021). Atomic IDs are supporting schedules that must reconcile to the annual view. `profit.net` and `profit.margin` keep those public IDs (Option A) and expect **already totalled** operating income and operating costs — use `pl.summary` when you still have the raw farm numbers. Loan repayments do not reduce Operating Surplus.

## Sample farm (`sample_data/farm.json`)

| Line | Amount |
|------|--------|
| Milk (100 × 5000 × €0.40) | €200,000 |
| Schemes | €25,000 |
| Cattle sales | €15,000 |
| **Operating income** | **€240,000** |
| **Operating costs** (excl. loans) | **€163,000** |
| **Operating Surplus** (`profit.net`) | **€77,000** |
| **Margin** | **32.08%** |
| Loan repayments (`finance`) | €12,000 |

Previously, including loans in costs produced €65,000 “profit”. Under ADR-0007 loans are finance-only.

## Run

Use a named local venv (prompt style `remote-functions`). Do not commit `.venv/`.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

**Windows cmd**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest
```

**Unix**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

**API**

- Non-reload (process entry): `python run_server.py`
- Local reload: `python -m uvicorn api.app:app --reload` (or `start.bat` on Windows)

**Service token (ADR-0049):** set `ENGINE_API_KEY` in `.env` (git-ignored) to require `Authorization: Bearer <key>` on `/v1/...`. Without it the engine is open, for local development only; `run_server.py` refuses a non-localhost `ENGINE_HOST` without a key.

On Windows, use `python -m uvicorn` (the bare `uvicorn` command is often not on PATH). Keep that terminal open, then call the API from another terminal or open http://127.0.0.1:8000/docs.

- `GET /livez` — liveness
- `GET /health` — liveness alias
- `GET /readyz` — readiness (200 once started, 503 otherwise)
- `GET /v1/functions` — discovery
- `GET /v1/functions/<key>` — input schema and units for one ID
- `POST /v1/functions/<key>/run` — one typed route per function (e.g. `revenue.milk`); body is a JSON object of numbers; OpenAPI shows the real field names
- `POST /v1/demo/pl-summary` — runs `pl.summary` on the sample farm
- OpenAPI: `http://127.0.0.1:8000/docs`

## Out of scope

Benchmarking against other farms, VAT, Monte Carlo, alerts, and farm-file loading from Dairy Financials.

## Docs

- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Domain model: [`docs/domain-model.md`](docs/domain-model.md)
- Development: [`docs/development.md`](docs/development.md)
- Delivery bootstrap (execute here): [`docs/delivery-bootstrap.md`](docs/delivery-bootstrap.md)
- External annual integration (I2): [`docs/integration-external.md`](docs/integration-external.md)
- API contract: [`docs/api-contract.md`](docs/api-contract.md)
- Decisions (ADRs): [`docs/decisions/`](docs/decisions/)

