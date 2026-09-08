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

For the current annual P&L it is the complete `pl.summary` driver set (`PlSummaryInput` / `FinancialInput`): required milk fields, optional scheme/other/cost lines defaulting to `0`. Numeric drivers must be finite numbers **≥ 0**. There is no maximum unless metadata sets one; none are set today.

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

For the current annual P&L it matches the existing `pl.summary` JSON: `currency`, `period`, nested `revenue`, `costs`, and `profit`. No extra result fields.

### Rounding

Published P&L outputs use **banker's rounding** (round half to even). See ADR-0005 and `farm_functions/rounding.py`.

- Formulas in `farm_functions/calcs/` stay full precision.
- Money (`EUR`) and `margin_pct`: 2 decimal places.
- `profit.margin` (0–1 ratio): 4 decimal places.
- Totals are rounded after the full-precision sum.
- Provenance values remain unrounded formula results.

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

Covered calculations: `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`, `profit.net`, `profit.margin`.

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
