# Development

Practical guide for working in this repository. Architecture and domain semantics live in `docs/architecture.md` and `docs/domain-model.md` — this file does not repeat them. The freeze-oriented **contract snapshot** and **Current Financial Domain Contract Scope** live in `docs/api-contract.md`. Branch `FINANCIAL-DOMAIN-CONTRACT` holds the technical freeze for review; do not treat merge to `main` as automatic.

## Local setup

Default is a named local venv (prompt style `remote-functions`). Do not commit `.venv/` (gitignored).

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Windows cmd:        .venv\Scripts\activate.bat
# Unix:               source .venv/bin/activate
python -m pip install -r requirements.txt
```

Process layout (composition root, lifespan, `run_server.py`, probes): [`delivery-bootstrap.md`](delivery-bootstrap.md).

## Run tests

```bash
python -m pytest
```

## Run the API

Non-reload process entry:

```bash
python run_server.py
```

Local reload:

```bash
python -m uvicorn api.app:app --reload
```

On Windows, prefer `python -m uvicorn` (or `start.bat`). OpenAPI: http://127.0.0.1:8000/docs. Liveness: `GET /livez` (and alias `GET /health`).

## Normal workflow

1. Read the relevant docs for the change (`docs/`, `CONTRIBUTING.md`, ADRs under `docs/decisions/`).
2. Implement the smallest change that satisfies the request.
3. Add or update tests.
4. Update docs when the contract or system behavior changes.
5. If the change alters an architectural decision, follow change-control (flag it; update or add an ADR).

## Adding or changing financial calculations

1. Keep formulas in `farm_functions/calcs/` pure (no I/O, HTTP, DB, auth).
2. Declare input models and `INPUT_FIELD_METADATA` / `FIELD_UNITS` in `farm_functions/schemas.py`. Units belong in `INPUT_FIELD_METADATA` so `FIELD_UNITS` stays derived from that list.
3. Register the calculation in `CALCULATION_CATALOGUE` in `farm_functions/registry.py` with an **explicit** public `id` (e.g. `revenue.milk`). Do not infer the public ID from the Python handler name. Required/optional fields and `INPUT_MODELS` are derived from that catalogue.
4. Set `supports_provenance` appropriately (`pl.summary` is false; atomic annual P&L lines are true).
5. Annual P&L domain types (`FinancialInput`, `FinancialModel`, `FinancialResult`) live in `farm_functions/domain.py` and must stay aligned with `pl.summary` — do not change formulas to fit the types.
6. Cover behavior in `tests/test_calcs.py`, `tests/test_runner.py`, and `tests/test_calculation_contract.py`. Domain-type tests live in `tests/test_domain.py`. Provenance tests live in `tests/test_provenance.py`. Do not change formulas to produce provenance; call the existing calculation functions.
7. Update `README.md` function table and `docs/domain-model.md` / `docs/api-contract.md` when semantics or the public contract change.

### Adding an operating cost category (Phase 1)

Authoritative catalogue: `OPERATING_COST_CATEGORIES` in `farm_functions/calcs/costs.py` (ADR-0007). To add a line:

1. Append the name to `OPERATING_COST_CATEGORIES` and to `total_costs(...)`.
2. Add an optional field on `TotalCostsInput` and a matching `INPUT_FIELD_METADATA` row.
3. Add the field on `CostLines` in `farm_functions/domain.py` and pass it through `pl_summary`.
4. Ensure the JSON loader picks it up via `COST_KEYS` / `OPERATING_COST_CATEGORIES`.
5. Update golden/reference cases and tests.

Do **not** add loan repayments, tax, drawings, depreciation, or capex as operating costs.

Never guess required missing inputs; the runner must return `needs_input`. Explicit `null` is invalid, not missing. Do not invent numeric maximums without a documented basis (ADR-0008: Phase 1 financial drivers have **no maximums**). Do not add cross-field farm-correlation rules or advisory “unusual value” rejection in this service (ADR-0008). Published P&L outputs use banker's rounding via `farm_functions/rounding.py` (ADR-0005). Internal numeric type for Phase 1 is `float` with publish-time rounding only (ADR-0006); do not silently migrate formulas to `Decimal`.

## Phase 1 validation vs advisory (ADR-0008)

| In this service | Not in this service (later / App Platform) |
|-----------------|--------------------------------------------|
| Finite ≥ 0 numbers; required/optional presence; null / type / unknown field errors | Farm benchmarking, “normal” ranges, KPIs |
| Independent inputs (except fields required to *run* a calculation) | Cross-field inference (cows → feed, etc.) |
| Explicit zero always valid for non-negative drivers | Soft warnings / anomaly alerts |

Characterisation: `tests/test_validation_independence.py`.

## Adding or changing API endpoints

1. Keep HTTP in `api/`; do not pull FastAPI into `farm_functions/calcs/`.
2. Prefer calling `run_function` / registry helpers rather than re-implementing validation.
3. Update `docs/api-contract.md`, README endpoint list, and `tests/test_api.py`.

## Testing expectations

- Financial behavior changes need tests.
- API/contract changes need API or runner contract tests.
- Prefer cases: normal, zeros, missing inputs, invalid inputs, boundaries, invariants.
- No mandated coverage percentage; use pytest as already configured.
- Registered calculation functions are covered by the behavior matrix in `tests/test_registered_functions.py` (happy path + edge cases via `run_function`, plus thin HTTP/OpenAPI smoke). Stable public calculation IDs are covered in `tests/test_calculation_contract.py`. Specialized suites cover validation, provenance, rounding, domain types, and pure formula units.
- Canonical annual P&L **golden / reference cases** live in `test-data/golden/` and are exercised by `tests/test_golden_reference_cases.py`. They lock published `pl.summary` / `FinancialResult` outputs (including Phase 1 Operating Surplus and `finance`, ADR-0007). Changing golden `expected` values must be deliberate and reviewed.
- Structured calculation **error codes** (`farm_functions/errors.py`, `tests/test_error_contract.py`) are the machine-readable failure contract for `run_function` / HTTP. Branch on `error.code`, not message text.
- Numeric **precision policy** characterisation lives in `tests/test_precision_policy.py` (ADR-0006): float internally, banker's rounding at publication, authoritative aggregate totals.
- Domain / API **alignment** regressions live in `tests/test_domain_api_alignment.py` (catalogue IDs ↔ discovery ↔ OpenAPI required fields).

## Documentation expectations

| Change type | Update |
|-------------|--------|
| Formulas / inputs / calculation IDs | README table; `CALCULATION_CATALOGUE` in `farm_functions/registry.py`; `docs/domain-model.md` for P&L meaning and validation; `INPUT_FIELD_METADATA` / `FIELD_UNITS` in `farm_functions/schemas.py` for units and constraints |
| Request/response / statuses | `docs/api-contract.md`, README Contract |
| Service boundary / auth / ownership | `docs/architecture.md`, `docs/security.md`, ADR |
| How to develop locally | this file |
| Process boot / venv / probes (FarmBiddy delivery principles) | `docs/delivery-bootstrap.md` |

## When to create an ADR

Create or update an ADR under `docs/decisions/` when you **change or firmly establish** an architectural decision (service boundary, trust model, persistence ownership, public contract shape, etc.).

Do **not** create empty or speculative ADRs for ideas that are still undecided.

## Current implementation vs target architecture

| Area | Current | Target (documented) |
|------|---------|---------------------|
| Calculations | Named functions + flat HTTP dicts; in-process `FinancialInput` / `FinancialModel` / `FinancialResult` for annual P&L | Same HTTP surface unless an explicit API decision changes it |
| Persistence | None (`FinancialModel` is in-memory only; sample JSON for demo) | App Platform owns models/scenarios |
| Auth | None on the API yet | Service-to-service auth; no user JWT for DB/RLS |
| Data access | Caller supplies numbers | App Platform builds FinancialInput; this service never queries Supabase |

Protect the **target boundary** (do not add Supabase, user auth, or persistence here). Do **not** treat missing target components as a mandate to implement them in the current task unless explicitly requested.
