# Financial Domain Model

## Core Concepts

The annual P&L is modelled as:

```text
FinancialModel
    ↓
FinancialInput
    ↓
canonical annual Operating Statement (`pl.summary`) and atomic schedule formulas
    ↓
FinancialResult
```

Python types: `farm_functions/domain.py`. They wrap current behaviour. They are **not** the HTTP surface.

### Period contracts (P1.1 / ADR-0018)

Annual types above are **frozen** for the Phase 1 annual facade (`Period = "annual"` only on `FinancialModel` / `FinancialResult`).

A separate **monthly** Domain contract exists for future monthly Operating Statements (calculation not implemented until P1.2):

```text
MonthlyDairyStatementModel
    period: MonthlyPeriodIdentity   # kind=month, year, month (identity only)
    currency
    inputs: MonthlyDairyFinancialInput   # milk_litres, milk_price, …
```

- Period identity (`year` / `month`) stays on the envelope — not on financial drivers and not passed into Core / Agriculture / Dairy formula primitives.
- Monthly milk drivers are `milk_litres` + `milk_price` (not annual `litres_per_cow`).
- Schemes, other income, operating costs, and `loan_repayments` reuse the same field names as annual, with monthly metadata units (`EUR` / `litres`) describing amounts for the stated month.
- Published income aggregates (`milk` / `schemes` / `other`) remain the monthly publication shape. Public HTTP: `pl.monthly` (ADR-0019).
- Monthly driver metadata: `MONTHLY_DAIRY_INPUT_FIELD_METADATA` in `farm_functions/schemas.py` (separate from annual `FIELD_UNITS`).
- **P1.2:** `calculate_monthly_dairy_statement(MonthlyDairyStatementModel)` returns `MonthlyDairyStatementResult` (structured `period` identity + reuse of revenue/costs/profit/finance money shapes). Dairy composes via `monthly_pl_summary` / `milk_revenue_from_litres` using explicit monthly amounts only (no annual ÷ 12).

### Cash Flow contracts (ADR-0022 / P3.1)

Cash Flow is **independent of P&L**. Explicit cash amounts for a month — not accruals, not annual÷12, not auto-mapped from `loan_repayments`.

```text
MonthlyDairyCashFlowModel
    period: MonthlyPeriodIdentity
    currency
    inputs: MonthlyDairyCashFlowInput   # operating / investing / financing catalogues
```

- Phase 1 catalogues include operating receipts/payments plus small investing and financing sets (`loan_proceeds`, `loan_principal_repayments`, `interest_paid`, capex/disposals).
- Phase 1 Dairy **input grouping** places `interest_paid` under financing outflows; Core does **not** encode that policy (D-CF1).
- Result shape `MonthlyDairyCashFlowResult`: per-activity inflows/outflows/net + `cash_in` / `cash_out` / `net_cash_flow`.
- No `calculate_*` cash entrypoint yet (P3.2). No opening/closing cash (P3.4). No household drawings yet (D-CF4). No cash HTTP yet.

### Multi-period P&L (ADR-0020)

**P2.1 (implemented, in-process only):** `MultiMonthDairyStatementModel` →
`calculate_multi_month_dairy_statements` → `MultiMonthDairyStatementResult`.

- Collection of **explicit** `MonthlyDairyStatementModel` values (min one).
- Each month runs existing `calculate_monthly_dairy_statement` (no new formulas).
- Duplicate `{year, month}` rejected; sparse and cross-year series allowed.
- Results sorted chronologically by `(year, month)`; caller order is not financial meaning.
- Result contains only `currency` + `months[]` — **not** YTD or cross-month totals.

**P2.2 (implemented, in-process only):** `YtdDairyStatementModel` →
`calculate_ytd_dairy_statement` → `YtdDairyStatementResult`.

- Identified by `year` + `as_of_month`; result `period.kind` is `"ytd"`.
- Requires contiguous January…`as_of_month` for that year; wrong-year months
  rejected; same-year months after `as_of_month` ignored.
- Reuses P2.1 multi-month → monthly calculator; aggregates with Core
  `sum_amounts` / `net_profit` / margins / publish rounding.
- **Not** annual÷12, **not** average of monthly margins, **not** equal to
  annual `pl.summary` by force. YTD ≠ annual.
- Cost catalogue lines summed per key so `CostsResult.lines` is complete;
  `costs.total` is the sum of monthly operating-cost totals (authoritative
  for surplus). Finance loans summed separately.

**P2.3 / P2.4 (ADR-0021):** Jan–Dec actual financial series needs **no new Domain
type** — P2.1 `months[]` is sufficient for charts. Public HTTP ID **`pl.months`**
is live: nested `months[]` + optional `ytd` → Domain multi-month + optional YTD
dumps (`result.ytd` is `null` when unused). Keep `pl.summary` / `pl.monthly`
unchanged.

`pl.summary` is the Phase 1 **canonical annual Operating Statement** (ADR-0009): the public annual calculation that returns the full `{currency, period, revenue, costs, profit, finance}` view. Atomic catalogue IDs are supporting schedules; for the same inputs their published results must reconcile with `pl.summary`. `calculate_annual_pnl` wraps the same composition and does not introduce alternate maths.

### FinancialInput

Normalized inputs required to perform a financial calculation.

FinancialInput is independent of the underlying farm database schema.

For the current annual P&L it is the complete `pl.summary` driver set (`PlSummaryInput` / `FinancialInput`): required milk fields, optional schemes, Dairy other income (`cattle_sales`, `land_leasing_income`, `other`), optional **operating cost** lines defaulting to `0`, plus optional `loan_repayments` (finance). Numeric drivers must be finite numbers **≥ 0**. There is no maximum unless metadata sets one; **none are set** (ADR-0008). Inputs are independent except for fields required to run a named calculation; the engine does not enforce farm correlations or “realistic” ranges (ADR-0008).

Operating cost lines are listed in `OPERATING_COST_CATEGORIES` (`farm_functions/dairy/costs.py`; `calcs.costs` re-exports), including `water`. **Phase 1 ownership (ADR-0013 / ADR-0015):** these farmer-entered cost lines are **Dairy-owned** on the current contract; a shared Agriculture cost catalogue is deferred. `rent_lease` is land/property rented **in** (cost); `land_leasing_income` is leasing owned land **out** (income) — they are not netted. Conceptually `land_leasing_income` is an **Agriculture** land semantic that remains on the Dairy Phase 1 input contract (ADR-0013). Loan repayments are finance/debt service and are **not** operating costs (ADR-0007). Sheep-oriented fields (`lamb_sales`, `wool`) are not part of the Dairy prototype contract.
Input metadata (name, type, required, minimum, maximum, unit, description) lives in `INPUT_FIELD_METADATA` in `farm_functions/schemas.py`. Units are taken from that list via `FIELD_UNITS` (ADR-0004).

**Sample JSON → flat drivers:** Demo [`sample_data/farm.json`](../sample_data/farm.json) is nested (`revenue` / `costs` / `finance`). `farm_functions.loaders.json_loader` flattens it to the flat field dict expected by `FinancialInput` and HTTP/`run_function`. Do not treat the nested sample shape as the HTTP body contract.

**Financial labels:** Human-readable names for public calculation IDs come from `CALCULATION_CATALOGUE` `description` (discovery `description`). Example: `profit.net` → Operating Surplus (ADR-0007). See `docs/api-contract.md` Phase 1 public surface freeze.

### Zero, missing, null, and invalid

| Case | Behaviour |
|------|-----------|
| Explicit `0` | Valid. Used as zero in the formula. |
| Required field **omitted** | `needs_input`. Not guessed. |
| Optional field **omitted** | Treated as `0`. |
| `null` on a known field | Invalid (`error`). Null is not a missing value. |
| Negative number | Invalid (`error`). |
| Wrong type (string, boolean, …) | Invalid (`error`). Not coerced. |

Direct formula functions in `farm_functions/calcs/` still take numbers only; this validation applies at `FinancialInput` / `PlSummaryInput` and `run_function`.

### FinancialResult

Structured result of a calculation.

For the current annual P&L it matches `pl.summary` JSON: `currency`, `period`, nested `revenue`, `costs`, `profit`, and `finance` (ADR-0007).

- `revenue` — operating income split (milk, schemes, other, total)
- `costs` — operating cost `lines` + `total` (excludes loan repayments)
- `profit.net` — Phase 1 **Operating Surplus** (operating income − operating costs); public ID kept (naming Option A, ADR-0009)
- `profit.margin` / `margin_pct` — Operating Surplus margin (public ID kept)
- `finance.loan_repayments` — debt service reported separately; does not reduce Operating Surplus

Phase 1 is a basic annual Operating Statement, not full accounting net profit (no depreciation, tax, drawings, livestock valuation, etc.).

### Rounding and numeric precision

**Precision** (internal representation) and **rounding** (publication) are distinct. See ADR-0006 and ADR-0005.

Published P&L outputs use **banker's rounding** (round half to even). See ADR-0005 and `farm_functions/rounding.py`.

- Validated inputs and formulas use Python `float` (IEEE-754). No intermediate business rounding in `farm_functions/calcs/`.
- Money (`EUR`) and `margin_pct`: 2 decimal places at publication.
- `profit.margin` (0–1 ratio): 4 decimal places at publication.
- Aggregate totals are calculated from underlying values, then rounded once. Independently rounded line items are presentation values and need not re-sum to the published total; the published aggregate is authoritative.
- Provenance values remain unrounded formula results.
- Binary floating-point may not represent some decimals exactly (for example `0.1 + 0.2`); publish-time rounding defines the public money/margin contract for Phase 1.
- Decimal / fixed-point migration is deferred until reassessment triggers in ADR-0006 apply.

Do not use raw `round()` for published P&L figures.

### Calculation provenance

Structured explainability for the existing annual P&L calculations lives in `farm_functions/provenance.py` (`explain_annual_pnl`). See ADR-0010.

```text
CalculationProvenance
├── calculation      # public calculation ID
├── value            # unrounded formula result
├── formula          # operation metadata (not a second calculator)
├── inputs_used      # name, value, unit for each operand
└── unit             # e.g. EUR/year or ratio
```

#### Explainability assembly (Phase 1)

1. **Calculation evidence** — Call `explain_annual_pnl` for the seven underlying calculations with `supports_provenance=True`:
   `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`.
   Each record already provides calculation ID, inputs used, formula/operation, calculated value, and unit. Do not change that shape for Phase 1.
2. **Canonical Operating Statement** — `pl.summary` is the authoritative combined annual view (ADR-0009). It does **not** have a separate duplicated provenance object (`supports_provenance=False`). Explain its financial calculations by using the seven component provenance records for the same drivers.
3. **Finance** — Read `loan_repayments` from `pl.summary` / `FinancialResult.finance`. It is a finance/debt passthrough on the statement: it appears in the annual result, stays separate from operating costs, and is **not** an input to `profit.net` or `profit.margin` provenance (or to Operating Surplus maths).
4. **Financial labels** — Human-readable meaning comes from catalogue `description` and documented semantics (ADR-0007 / ADR-0009), not from renaming IDs:
   - `profit.net` → **Operating Surplus**
   - `profit.margin` → **Operating Surplus Margin**
5. **Precision** — Provenance values may be **unrounded** calculation evidence. Published aggregate totals remain authoritative (ADR-0005 / ADR-0006). Do not treat independently rounded published lines as a second source of truth that must re-sum to provenance.
6. **HTTP boundary** — Phase 1 provenance is **in-process only**. It is not exposed on `/v1/functions/.../run` and there is no `/explain` endpoint. A future API/platform/agent may consume or present this evidence separately.
7. **Engine vs agent** — The financial engine supplies deterministic calculation facts. Natural-language commentary, advice, or conversational explanation belongs to a future agent/platform layer — not this service.

- Existing calculation functions remain **authoritative**. Provenance records how a result was produced; it does not replace or reimplement the formula.
- Provenance is structured evidence for UI / Agent presentation. It is not natural-language prose.

### Simulation (input overrides)

In-process simulation applies **explicit** caller-supplied changes to a **copy** of `FinancialInput` and reruns the canonical annual model (ADR-0011). Implementation: `farm_functions/simulation.py` (`simulate_annual_pnl`).

```text
base FinancialInput
+ explicit overrides
→ validated FinancialInput (copy; base unchanged)
→ calculate_annual_pnl (base) and calculate_annual_pnl (simulated)
→ SimulationResult { base, simulated, overrides_applied }
```

- Simulation contains **no** financial formulas — only merge + `calculate_annual_pnl`.
- Override keys must be existing `FinancialInput` fields; unknown keys are rejected. Merged values use the same B3 validation as normal inputs.
- Only named fields change (ADR-0008 independence). Multiple overrides are allowed; no cross-field inference.
- Returns base and simulated `FinancialResult` for comparison. No engine-side deltas or favourable/unfavourable labels.
- Not forecasting, sensitivity ranges, or Monte Carlo. Named assumption packages are **scenarios** (ADR-0012) built on this primitive.
- **Not on HTTP** in Phase 1. Provenance for a simulated run: call `explain_annual_pnl` on the simulated `FinancialInput` (ADR-0010).

### Scenarios (named assumption packages)

In-process scenarios package explicit overrides under a caller-defined name and execute them through B7 simulation (ADR-0012). Implementation: `farm_functions/scenarios.py` (`run_scenario`, `run_scenarios`).

```text
ScenarioDefinition { name, overrides }
+ base FinancialInput
→ SimulationRequest → simulate_annual_pnl (B7)
→ ScenarioResult { name, overrides_applied, result }

run_scenarios → ScenarioBundle { base, scenarios[] }  # caller order; independent runs
```

- A scenario is **name + assumptions**, not a forecast. `milk_price = 0.35` means calculate **if** milk were €0.35/L.
- B8 owns non-blank name validation only. Financial override validation remains B7 / `FinancialInput`.
- Every scenario starts from the original base (Scenario B does not inherit Scenario A).
- Duplicate names allowed (positional). No Base/Best/Worst engine types, ranking, deltas, or persistence.
- Empty overrides are valid (named current-position case).
- **Not on HTTP** in Phase 1. Persistence of scenario libraries belongs to the App Platform (ADR-0003).

### FinancialModel

In this service, an **in-memory envelope** only:

- `period`: `"annual"`
- `currency`: `"EUR"`
- `inputs`: `FinancialInput`

Units: period is `annual`; currency is `EUR`. See `INPUT_FIELD_METADATA`.

It is **not** stored here. No `farm_id`, `model_id`, timestamps, scenarios, or calculation version.

The App Platform may persist a farm financial model. That persistence does not live in this repository (ADR-0003).

### Scenario

See **Scenarios (named assumption packages)** above. Ephemeral in-process definitions only; App Platform owns save/commit of scenario libraries (ADR-0003).

## Ownership

Database/source data:
    App Platform

FinancialInput:
    App Platform constructs it

Financial calculations:
    Financial Service (stateless; existing functions in `farm_functions/calcs/`)

FinancialResult:
    Financial Service produces it

FinancialModel in this process:
    In-memory envelope only; not written to a database

Persisted model/scenario:
    App Platform owns persistence

## HTTP

HTTP behaviour is unchanged: named functions, flat JSON input, `ok` / `needs_input` / `error`. See `docs/api-contract.md`.
