# Development

Practical guide for working in this repository. Architecture and domain semantics live in `docs/architecture.md` and `docs/domain-model.md` — this file does not repeat them.

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
2. Declare per-function inputs in `farm_functions/schemas.py` (`REQUIRED_FIELDS` / `OPTIONAL_FIELDS`, Pydantic models, and `INPUT_FIELD_METADATA` / `FIELD_UNITS`). Units belong in `INPUT_FIELD_METADATA` so `FIELD_UNITS` stays derived from that list. Annual P&L domain types (`FinancialInput`, `FinancialModel`, `FinancialResult`) live in `farm_functions/domain.py` and must stay aligned with `pl.summary` — do not change formulas to fit the types.
3. Register the function in `farm_functions/registry.py`.
4. Cover behavior in `tests/test_calcs.py` and/or `tests/test_runner.py`. Domain-type tests live in `tests/test_domain.py`. Provenance tests live in `tests/test_provenance.py`. Do not change formulas to produce provenance; call the existing calculation functions.
5. Update `README.md` function table and `docs/domain-model.md` / `docs/api-contract.md` when semantics or the public contract change.

Never guess required missing inputs; the runner must return `needs_input`. Explicit `null` is invalid, not missing. Do not invent numeric maximums without a documented basis. Published P&L outputs use banker's rounding via `farm_functions/rounding.py` (ADR-0005).

## Adding or changing API endpoints

1. Keep HTTP in `api/`; do not pull FastAPI into `farm_functions/calcs/`.
2. Prefer calling `run_function` / registry helpers rather than re-implementing validation.
3. Update `docs/api-contract.md`, README endpoint list, and `tests/test_api.py`.

## Testing expectations

- Financial behavior changes need tests.
- API/contract changes need API or runner contract tests.
- Prefer cases: normal, zeros, missing inputs, invalid inputs, boundaries, invariants.
- No mandated coverage percentage; use pytest as already configured.
- Registered calculation functions are covered by the behavior matrix in `tests/test_registered_functions.py` (happy path + edge cases via `run_function`, plus thin HTTP/OpenAPI smoke). Specialized suites cover validation, provenance, rounding, domain types, and pure formula units.

## Documentation expectations

| Change type | Update |
|-------------|--------|
| Formulas / inputs | README table; `docs/domain-model.md` for P&L meaning and validation; `INPUT_FIELD_METADATA` / `FIELD_UNITS` in `farm_functions/schemas.py` for units and constraints |
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
