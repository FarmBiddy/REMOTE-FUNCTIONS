# API Contract

Canonical description of the Financial Service HTTP calculation contract.
Implementation: `farm_functions/registry.py` (authoritative catalogue), `farm_functions/runner.py`, `farm_functions/schemas.py`, `api/app.py` (composition root), `api/routes.py` (HTTP handlers).

For a separate frontend (e.g. Next.js mock) integrating annual or monthly Operating Statements over HTTP, start with [`integration-external.md`](integration-external.md) (I2 / P1.4: request/response map, error branching, CORS).

Domain types (`FinancialModel` → `FinancialInput` → calculations → `FinancialResult`) live in `farm_functions/domain.py`. They do **not** change the annual/monthly HTTP contract: those request bodies remain a flat JSON object of numbers; statuses remain `ok` / `needs_input` / `error`. **Exception (ADR-0021 / P2.4):** `pl.months` uses a nested `months[]` array plus optional `ytd` object.

Annual P&L provenance (`explain_annual_pnl`) is in-process only. It is not included in HTTP calculation responses.

## Contract snapshot

**Service:** Stateless annual dairy P&L calculator (validate inputs, run named calculations, return structured results).

**Calculations (30 public IDs):** `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`, `pl.summary`, `pl.monthly`, `pl.months`, `cf.monthly`, `cf.months`, `loan.schedule`, `assets.schedule`, `debt.capacity`, `kpi.summary`, `pl.net`, `bs.summary`, `pl.compare`, `cf.compare`, `risk.sensitivity`, `risk.tornado`, `decision.partial_budget`, `decision.investment`, `report.bank`, `report.advisor`, `report.accountant`, `plan.projection`, `pl.forecast`, `cf.forecast` — from `CALCULATION_CATALOGUE` only.

**Inputs:** Flat JSON numbers per calculation (except `pl.months`: nested `months[]` + optional `ytd`; `cf.months`: `opening_cash` + nested `months[]`). Required fields → `needs_input` when omitted; nested ones (inside `months[]`, `loans[]`, `history[]`, `forecast[]`) add `path`, e.g. `{"field":"milk_price","unit":"EUR/litre","path":"months[3].milk_price"}`, as long as nothing else is invalid (ADR-0027). Optional omitted → `0` (or `ytd: null` / omitted for months-only). Explicit `0` is valid. Unknown fields / null / negatives / wrong types → `error` with stable codes. Units come from one table (`field_unit`) used by both `needs_input` and `GET /v1/functions/{id}` (ADR-0048).

**Outputs:** Money calculations → `{amount, currency:"EUR"}`. `profit.margin` → margin object. `pl.summary` / in-process `FinancialResult` → `{currency, period, revenue, costs, profit, finance}` with `period:"annual"`. `pl.monthly` → same money nests with `period: {kind, year, month}` (ADR-0019). `pl.months` → `{currency, months: MonthlyDairyStatementResult[], ytd: YtdDairyStatementResult | null}` — Domain dumps; no chart DTOs. `cf.monthly` → `MonthlyDairyCashFlowResult` dump: `{currency, period, operating, investing, financing, cash_in, cash_out, net_cash_flow}`; each activity `{inflows:{lines,total}, outflows:{lines,total}, net}`; every catalogue line published (zeros included); `opening_cash` / `closing_cash` (`null` unless `opening_cash` sent). `cf.months` → `{currency, opening_cash, months: MonthlyDairyCashFlowResult[], cash_in, cash_out, net_cash_flow, closing_cash}`; months consecutive (gap → `details.reason: non_contiguous_months`); `opening_cash` may be negative (ADR-0024). `loan.schedule` takes `{loans: [{balance, annual_rate, remaining_months, year, month, original_principal?, variable? (default false)}]}` (1–50) → `{currency, loans[], total_balance, total_monthly_payment, total_interest, months[{period, payment, interest, principal}]}` (combined debt service); each `loans[]` item `{balance, annual_rate, remaining_months, monthly_payment, total_interest, total_payments, repaid_pct, months[{period, opening_balance, payment, interest, principal, closing_balance}]}` in input order (ADR-0025). `annual_rate` is a 0–1 ratio (`4.2` → error); `repaid_pct` is `null` unless `original_principal` is sent; `original_principal < balance` → `details.reason: principal_below_balance`. `kpi.summary` takes `{months: [pl.months items], milking_cows, milk_solids_kg?, hectares?, debt_balance?}` → `{currency, from, to, month_count, milking_cows, totals{milk_litres, revenue, costs, operating_surplus, loan_repayments}, per_litre_c{revenue, costs, variable_costs, fixed_costs, gross_margin, operating_surplus, cost_lines{...}}, per_cow{milk_litres, revenue, costs, gross_margin, operating_surplus}, per_kg_ms{revenue, costs, gross_margin, operating_surplus} | null, per_hectare{milk_litres, revenue, costs, gross_margin, operating_surplus} | null, debt{balance, per_cow, per_hectare} | null, dscr}`; a block is `null` when its optional input is not sent; ratios with a 0 divisor are `null` (ADR-0028, ADR-0032, ADR-0033). `pl.net` takes `{months[], depreciation?, interest?, livestock_opening_value?, livestock_closing_value?, stock_opening_value?, stock_closing_value?}` → `{currency, from, to, month_count, revenue, operating_surplus, livestock_value_change, stock_value_change, adjusted_surplus, depreciation, ebit, interest, net_profit_before_tax, net_margin_pct}`; only interest is an expense, never principal (ADR-0038). `risk.tornado` takes the `risk.sensitivity` base `{pl_months[], cf_months[], opening_cash, loans?, shocks_from_*?}` plus `step_pct?` (default 10), `rate_step_pp?` (default 1), `rank_by?` (`operating_surplus` | `closing_cash` | `lowest_cash`) → `{currency, step_pct, rate_step_pp, rank_by, base{operating_surplus, closing_cash, lowest_cash, dscr}, drivers[{driver, shock, low_change, high_change, low{…}, high{…}, swing{operating_surplus, closing_cash, lowest_cash}}]}` sorted by swing; only lines with an amount, interest rate only with variable loans (ADR-0044). `decision.partial_budget` takes `{added_income?, reduced_costs?, added_costs?, reduced_income?: [{label, amount}], capital?{amount, life_years, annual_rate?}}` (annual amounts) → `{currency, added_income{items, total}, reduced_costs{…}, added_costs{…}, reduced_income{…}, gains, losses, operating_change, capital{depreciation, interest, annual_charge, simple_payback_years, return_on_investment_pct} | null, net_change, worthwhile}`; capital charge = depreciation + interest on half the capital (ADR-0045). `decision.investment` takes `{amount, discount_rate, annual_benefit + life_years | cash_flows[], residual_value?}` → `{currency, amount, discount_rate, life_years, residual_value, npv, irr_pct, simple_payback_years, discounted_payback_years, profitability_index, worthwhile, years[{year, cash_flow, discount_factor, present_value, cumulative_present_value}]}`; `irr_pct` / paybacks `null` when not reached; one benefit form only (`benefit_form`) (ADR-0046). `plan.projection` takes `{base_pl_months (12 consecutive), opening_cash, milking_cows, years? (1–10, default 5), assumptions?{milk_price[], herd_pct[], yield_pct[], cost_inflation_pct[], lines_inflation_pct{line: []}, lines_amount{line: []}, drawings[], tax[], off_farm_income[], interest_rate_shift_pp[]}, loans?, assets?, investments?[{year, amount, life_months, category?, loan?, annual_effects?}], land?, livestock?, min_cover?}` → `{currency, base, years[{year, period, assumptions_used, pl, cash, debt, balance_sheet, kpis, flags}]}`. Per-year lists: index 0 = year 1; prices and amounts carry forward, % changes default to 0; no assumptions = base year repeated. Reasons `base_not_12_consecutive`, `assumption_longer_than_years`, `investment_outside_years` (ADR-0042). `report.bank` / `report.advisor` / `report.accountant` take the same farm file `{pl_months[], cf_months[] (same last month), opening_cash, milking_cows, hectares?, milk_solids_kg?, prior_pl_months?, projected_pl_months?, projected_cf_months?, loans?, assets?, debtors?, stock?, livestock?, land?, creditors?, other_long_term_liabilities?, livestock_opening_value?, stock_opening_value?, drawings?, tax?, off_farm_income?, new_loan?{annual_rate, term_months, min_cover?}, scenarios?}` and return `{report, currency, as_of, period, …sections}`: bank `profit, kpis, loans, capacity, balance_sheet, cash{actual, projection}`; advisor `kpis, profit, comparison, sensitivity`; accountant `profit_and_loss, net_profit, fixed_assets, balance_sheet, cash_flow`. Each section is the output of the matching ID; reasons `periods_misaligned`, `projection_overlaps_period` (ADR-0041). `bs.summary` takes `{year, month, cash? (signed), debtors?, stock?, livestock?, land?, creditors?, other_long_term_liabilities?, loans? (loan.schedule items), assets? (assets.schedule items)}` → `{currency, as_of, assets{current{cash, debtors, stock, total}, non_current{land, buildings, machinery, other_fixed_assets, livestock, total}, total}, liabilities{current{overdraft, creditors, loans_due_within_12_months, total}, non_current{loans_due_after_12_months, other_long_term_liabilities, total}, total}, net_worth, ratios{equity_pct, debt_to_assets_pct, current_ratio, working_capital}}`; livestock excluded from the current ratio (ADR-0039). `assets.schedule` takes `{assets: [{category?, cost, year, month, method? (straight_line | reducing_balance), life_months?, residual_value?, annual_rate?}], from_year, from_month, to_year, to_month}` → `{currency, from, to, assets[], by_category{machinery, buildings, other}, total}`, each a note `{opening_nbv, additions, depreciation, closing_nbv}` that reconciles to the cent; reasons `method_needs_field`, `residual_above_cost`, `period_reversed` (ADR-0037). `debt.capacity` takes `{months[], annual_rate, term_months, drawings?, tax?, off_farm_income?, min_cover? (≥1, default 1)}` → `{currency, from, to, month_count, operating_surplus, off_farm_income, drawings, tax, repayment_capacity, debt_service, repayment_cover, min_cover, new_loan{annual_rate, term_months, max_monthly_payment, max_principal, monthly_payment_at_max}}`; `max_principal` rounded down; `repayment_cover` `null` without current debt (ADR-0036). `pl.compare` / `cf.compare` take `{actual: [months], comparison: [months]}` (prior year or budget; item shapes of `pl.months` / `cf.months`) → `{currency, actual{from, to, month_count}, comparison{…}, …statement tree}` where every money leaf is `{actual, comparison, change, change_pct}` (`change_pct` `null` when comparison is 0); `pl.compare` adds `margin_pct{actual, comparison, change_pp}` and `milk{litres, price_c, volume_effect, price_effect}`; `cf.compare` compares movements only, no balances (ADR-0035). `risk.sensitivity` takes `{pl_months[], cf_months[] (consecutive), opening_cash, loans? (loan.schedule items behind the months' loan lines), scenarios?: [{name?, milk_price_c?, milk_volume_pct?, herd_pct?, rate_shift_pp? (variable loans reprice), lines_pct?: {line: %}, investments?: [{year, month, amount, cash_line?, loan?: {amount, annual_rate, remaining_months}, monthly_effects?: {line: ±EUR}}] (≤5)}] (≤20)}` → `{currency, milk_price_c, scenarios[{name, shocks, investments[{period, amount, loan_monthly_payment, monthly_benefit, simple_payback_months}], operating_surplus, loan_repayments, dscr, closing_cash, lowest_cash{period, amount}, overdraft_months, break_even{surplus_milk_price_c, cash_milk_price_c}}]}`; `scenarios[0]` is always `base`; break-evens `null` when not computable; investment outside `cf_months` → `details.reason: investment_outside_months`; `herd_pct` scales litres, variable costs and cattle sales, not fixed costs or schemes; optional `shocks_from_year` / `shocks_from_month` keep earlier months as history (no shocks; break-evens, `lowest_cash` and `overdraft_months` from that month on; echoed as `shocks_from`) (ADR-0029, ADR-0031, ADR-0033, ADR-0040). `pl.forecast` / `cf.forecast` take `{history: [actual month items], forecast: [{year, month, ...known values}]}` and return `{currency, as_of, run_rate, months[]}`; each month `{period, inputs, statement | cash_flow}` where `inputs` plug into `pl.months` / `cf.months` (ADR-0026). Errors: `forecast_overlaps_history`, `missing_prior_year_month`, `duplicate_period`. In forecast items an omitted or `null` line means "project it".

**Canonical annual view (ADR-0009):** `pl.summary` is the Phase 1 **canonical annual Operating Statement**. Atomic catalogue IDs remain supporting schedules and must reconcile to `pl.summary` for the same inputs (published aggregates authoritative per ADR-0005). In-process `calculate_annual_pnl` wraps the same composition.

**Phase 1 financial meaning (ADR-0007; naming Option A, ADR-0009):** Public IDs `profit.net` / `profit.margin` are kept for API compatibility; their meaning is **Operating Surplus** / Operating Surplus margin (operating income − operating costs). `costs.total` and `costs.lines` are **operating costs only**. `loan_repayments` is reported under `finance` and does **not** reduce Operating Surplus. This is not full accounting net profit.

**Validation:** Codes `missing_required`, `unknown_field`, `null_not_allowed`, `negative_value`, `invalid_type`, `non_finite_value`, `unknown_calculation`. Branch on `error.code`, not message text.

### Conventions (ADR-0050)

**HTTP status.** Calculation routes answer **200**; the outcome is in `status`
(`ok` / `needs_input` / `error`). HTTP codes are only for transport: 401
`unauthorized` (service token, ADR-0049), 404 unknown ID on
`GET /v1/functions/{id}`. Malformed JSON → `error` with `invalid_json`.

**Meta.** Every run envelope carries `meta.engine_version` (e.g. `"1.0.0"`);
quote it in reports.

**Limits.** Month lists ≤ 120 items; per-year assumption lists ≤ 10; other lists
as documented per ID (loans ≤ 50, assets ≤ 200, scenarios ≤ 20 …).

**Glossary.**

| Term | Field(s) | Meaning |
|---|---|---|
| Operating Surplus | `operating_surplus`; `profit.net` in `pl.*` | Operating income − operating costs (before depreciation, interest, loan principal, drawings, tax) |
| Gross margin | `gross_margin` | Revenue − variable costs (ADR-0033) |
| Net profit before tax | `net_profit_before_tax` | Operating Surplus ± valuation changes − depreciation − interest (ADR-0038) |
| Debt service | `debt_service`, `loan_repayments` | Interest + principal paid |
| DSCR | `dscr` | Operating Surplus / debt service |
| Repayment cover | `repayment_cover` | (Operating Surplus + off-farm − drawings − tax) / debt service |

**Units.** Money `EUR`; `annual_rate` / `discount_rate` are 0–1 ratios (0.042 =
4.2%); `*_pct` are percentages (10 = 10%); `*_pp` are percentage points;
`milk_price` is EUR/L, `milk_price_c` c/L. Every field's unit is in
`GET /v1/functions/{id}` → `units` (ADR-0048).

**Phase 1 validation principles (ADR-0008):** Validation checks whether inputs are **structurally usable** for the calculation (finite ≥ 0, presence, types). It does **not** judge whether farm numbers are normal, efficient, or commercially good. Financial inputs are **independent** except where a field is required to run a named calculation (e.g. milk trio for `revenue.milk`). No Phase 1 **maximums**. No calculation-engine warning / advisory / benchmark channel. Unusual-but-valid values (e.g. high contractor cost, `milk_price = 0`, zero cows with positive litres) remain `ok`.

**Precision:** Internal `float` (ADR-0006); publish with banker's rounding (ADR-0005); published aggregate totals are authoritative; rounded lines need not re-sum exactly; provenance stays unrounded.

**Provenance (ADR-0010):** In-process `explain_annual_pnl` for the seven catalogue entries with `supports_provenance=True`. `pl.summary` has no separate provenance object — explain it via those seven component records plus `finance` from the statement result. Human labels for `profit.net` / `profit.margin` come from catalogue / ADR-0007 (Operating Surplus / margin). Provenance stays unrounded; published aggregates remain authoritative. **Not on HTTP** (no Phase 1 `/explain` endpoint). Natural-language explanation belongs to a future agent/platform layer.

**What-if scenarios:** HTTP `risk.sensitivity` (ADR-0029, ADR-0031, ADR-0033). The former in-process annual `simulate_annual_pnl` / `run_scenarios` were removed (ADR-0034).

**Out of scope on HTTP today:** persistence, authentication, multi-currency, AI-generated calculations, Supabase/farm CRUD. Multi-period OS is available as `pl.months` (ADR-0021); forecasting as `pl.forecast` / `cf.forecast` (ADR-0026); Dairy KPIs as `kpi.summary` (ADR-0028).

### Intentional interface differences

| Layer | Representation |
|-------|----------------|
| HTTP / runner | Flat per-calculation field dict; **exception** `pl.months` nested `months[]` + optional `ytd` (ADR-0021; P2.4) |
| Domain | Annual envelope; monthly / multi-month / YTD envelopes in-process (P2.1–P2.2) |
| Discovery | `GET /v1/functions`: `key`, `description`, `required`, `optional`; `GET /v1/functions/{id}`: plus `units` for every field and the JSON `input_schema` incl. nested items (ADR-0048) |
| Provenance | Unrounded formula values via `explain_annual_pnl`; not on HTTP; `pl.summary` explained by components + `finance` (ADR-0010) |
| What-if scenarios | HTTP `risk.sensitivity` (ADR-0029); in-process B7/B8 removed (ADR-0034) |

Do **not** force HTTP to accept `FinancialModel`. Numeric bounds enforced by custom validators (e.g. 0–1 rates) are documented here, not in `input_schema`.

## Phase 1 public surface (freeze)

This section freezes what App Platform integrations may depend on after Workstream B (B1–B8). It invents no new behaviour.

### HTTP calculation surface

Supported endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/livez`, `/health` | Liveness |
| `GET` | `/v1/functions` | Discovery (`key`, `description`, `required`, `optional`) |
| `GET` | `/v1/functions/<calculation_id>` | Input schema + units for one ID (404 if unknown) |
| `POST` | `/v1/functions/<calculation_id>/run` | Run one registered calculation |
| `POST` | `/v1/demo/pl-summary` | Demo: `pl.summary` on sample farm |

**Ten registered calculation IDs** (`CALCULATION_CATALOGUE` only):

`revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`, `pl.summary`, `pl.monthly`, `pl.months`, `cf.monthly`, `cf.months`, `loan.schedule`, `assets.schedule`, `debt.capacity`, `kpi.summary`, `pl.net`, `bs.summary`, `pl.compare`, `cf.compare`, `risk.sensitivity`, `risk.tornado`, `decision.partial_budget`, `decision.investment`, `report.bank`, `report.advisor`, `report.accountant`, `plan.projection`, `pl.forecast`, `cf.forecast`

HTTP request/response envelopes use statuses `ok` / `needs_input` / `error`. On failure, branch on structured `error.code` (see Validation above), not message text.

### In-process Python surface

Package exports (`farm_functions`):

| Symbol | Role | On HTTP? |
|--------|------|----------|
| `run_function` / `list_functions` / `list_input_metadata` | Same catalogue as HTTP | HTTP uses these internally |
| `calculate_annual_pnl` | Canonical annual `FinancialResult` from `FinancialModel` | No — in-process only |
| `explain_annual_pnl` | Deterministic calculation provenance (ADR-0010) | No — in-process only |
| `FinancialInput` / `FinancialModel` / `FinancialResult` | Typed annual P&L domain | No — not the HTTP body shape |
| `CalculationProvenance` | Provenance record type | No |

Phase 1 does **not** expose an HTTP endpoint for provenance. What-if scenarios are HTTP `risk.sensitivity`.

### Stable IDs and financial labels

- Calculation **IDs** are stable technical identifiers (including `profit.net` and `profit.margin`).
- Human-readable financial **labels** come from the catalogue `description` on each `CALCULATION_CATALOGUE` entry (also returned by discovery as `description`). That is the authoritative label source — do not invent a second label dictionary.
- Phase 1 meaning: `profit.net` = **Operating Surplus**; `profit.margin` = **Operating Surplus Margin** (ADR-0007). These IDs are not full accounting net profit.

### Error boundary (intentional)

| Path | How failures appear |
|------|---------------------|
| HTTP / `run_function` | Structured envelope: `needs_input` or `error` with stable `error.code` |
| In-process domain (`FinancialInput` / `FinancialModel`) | Python exceptions: typically Pydantic `ValidationError` and/or plain `ValueError` |

This split is **intentional** for Phase 1. There is no unified structured-error framework for in-process domain calls.

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
- Public HTTP discovery and execution (`/v1/functions`, `/run`, demo)
- Reconciliation, golden/reference, error, precision, and alignment regression tests
- Publication rounding (ADR-0005), Phase 1 float precision (ADR-0006), Operating Surplus (ADR-0007), validation independence (ADR-0008), canonical Operating Statement (ADR-0009), provenance boundary (ADR-0010)

### Not included (do not assume)

- Principal vs interest split for P&L `loan_repayments` (use `loan.schedule` rows for cash flow; ADR-0025)
- Tax, and accrual adjustments for debtors / creditors (net profit before tax: `pl.net`, ADR-0038)
- Advisory validation, farm benchmarking, anomaly detection, normal ranges, soft warnings, KPI thresholds
- Scenarios as persisted libraries / Base–Best–Worst engine types (HTTP what-ifs via `risk.sensitivity`, ADR-0029; persistence and judgement stay elsewhere)
- Asset valuation (land / livestock values are Platform inputs), optimisation
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
| `GET` | `/readyz` | Readiness: 200 after startup, 503 otherwise |
| `GET` | `/v1/functions` | Discovery (keys, descriptions, required/optional fields) |
| `GET` | `/v1/functions/<calculation_id>` | Input schema + units for one ID (ADR-0048) |
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
