# Financial Domain Model

## Core Concepts

The annual P&L is modelled as:

```text
FinancialModel
    ↓
FinancialInput
    ↓
existing calculation functions (`pl.summary` and the atomic formulas)
    ↓
FinancialResult
```

Python types: `farm_functions/domain.py`. They wrap current behaviour. They are **not** the HTTP surface.

### FinancialInput

Normalized inputs required to perform a financial calculation.

FinancialInput is independent of the underlying farm database schema.

For the current annual P&L it is the complete `pl.summary` driver set (`PlSummaryInput` / `FinancialInput`): required milk fields, optional scheme/other/**operating cost** lines defaulting to `0`, plus optional `loan_repayments` (finance). Numeric drivers must be finite numbers **≥ 0**. There is no maximum unless metadata sets one; **none are set** (ADR-0008). Inputs are independent except for fields required to run a named calculation; the engine does not enforce farm correlations or “realistic” ranges (ADR-0008).

Operating cost lines are listed in `OPERATING_COST_CATEGORIES` (`farm_functions/calcs/costs.py`). Loan repayments are finance/debt service and are **not** operating costs (ADR-0007).

Input metadata (name, type, required, minimum, maximum, unit, description) lives in `INPUT_FIELD_METADATA` in `farm_functions/schemas.py`. Units are taken from that list via `FIELD_UNITS` (ADR-0004).

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
- `profit.net` — Phase 1 **Operating Surplus** (operating income − operating costs); public ID unchanged
- `profit.margin` / `margin_pct` — Operating Surplus margin
- `finance.loan_repayments` — debt service reported separately; does not reduce Operating Surplus

Phase 1 is a basic annual operating P&L, not full accounting net profit (no depreciation, tax, drawings, livestock valuation, etc.).

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

Structured explainability for the existing annual P&L calculations lives in `farm_functions/provenance.py` (`explain_annual_pnl`).

```text
CalculationProvenance
├── calculation
├── value
├── formula
├── inputs_used   # name, value, unit for each operand
└── unit
```

Covered calculations: `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin` (catalogue entries with `supports_provenance=True` in `farm_functions/registry.py`). `pl.summary` has no provenance entry.

- Existing calculation functions remain **authoritative**. Provenance records how a result was produced; it does not replace or change the formula.
- Provenance is for UI / Agent explainability. It is not natural-language prose.
- Provenance is **not** added to the HTTP `pl.summary` (or other `/v1/functions/.../run`) response. Call `explain_annual_pnl` in-process.

### FinancialModel

In this service, an **in-memory envelope** only:

- `period`: `"annual"`
- `currency`: `"EUR"`
- `inputs`: `FinancialInput`

Units: period is `annual`; currency is `EUR`. See `INPUT_FIELD_METADATA`.

It is **not** stored here. No `farm_id`, `model_id`, timestamps, scenarios, or calculation version.

The App Platform may persist a farm financial model. That persistence does not live in this repository (ADR-0003).

### Scenario

A set of overrides applied to a FinancialModel without modifying
the underlying model.

Scenarios are not implemented in this service. If added later, calculations stay ephemeral here; save/commit stays on the App Platform.

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
