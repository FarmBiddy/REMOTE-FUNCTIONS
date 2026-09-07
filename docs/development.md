# Development

Practical guide for working in this repository. Architecture and domain semantics live in `docs/architecture.md` and `docs/domain-model.md` — this file does not repeat them.

## Local setup

```bash
python -m pip install -r requirements.txt
```

Use a virtual environment if you prefer (`.venv/` is gitignored).

## Run tests

```bash
python -m pytest
```

## Run the API

```bash
python -m uvicorn api.app:app --reload
```

On Windows, prefer `python -m uvicorn` (or `start.bat`). OpenAPI: http://127.0.0.1:8000/docs

## Normal workflow

1. Read the relevant docs for the change (`docs/`, `CONTRIBUTING.md`, ADRs under `docs/decisions/`).
2. Implement the smallest change that satisfies the request.
3. Add or update tests.
4. Update docs when the contract or system behavior changes.
5. If the change alters an architectural decision, follow change-control (flag it; update or add an ADR).

## Adding or changing financial calculations

1. Keep formulas in `farm_functions/calcs/` pure (no I/O, HTTP, DB, auth).
2. Declare inputs in `farm_functions/schemas.py` (`REQUIRED_FIELDS` / `OPTIONAL_FIELDS`, Pydantic models, and `FIELD_UNITS` for any new fields).
3. Register the function in `farm_functions/registry.py`.
4. Cover behavior in `tests/test_calcs.py` and/or `tests/test_runner.py`.
5. Update `README.md` function table and `docs/domain-model.md` / `docs/api-contract.md` when semantics or the public contract change.

Never guess required missing inputs; the runner must return `needs_input`.

## Adding or changing API endpoints

1. Keep HTTP in `api/`; do not pull FastAPI into `farm_functions/calcs/`.
2. Prefer calling `run_function` / registry helpers rather than re-implementing validation.
3. Update `docs/api-contract.md`, README endpoint list, and `tests/test_api.py`.

## Testing expectations

- Financial behavior changes need tests.
- API/contract changes need API or runner contract tests.
- Prefer cases: normal, zeros, missing inputs, invalid inputs, boundaries, invariants.
- No mandated coverage percentage; use pytest as already configured.

## Documentation expectations

| Change type | Update |
|-------------|--------|
| Formulas / inputs | README table; domain docs if concepts change |
| Request/response / statuses | `docs/api-contract.md`, README Contract |
| Service boundary / auth / ownership | `docs/architecture.md`, `docs/security.md`, ADR |
| How to develop locally | this file |

## When to create an ADR

Create or update an ADR under `docs/decisions/` when you **change or firmly establish** an architectural decision (service boundary, trust model, persistence ownership, public contract shape, etc.).

Do **not** create empty or speculative ADRs for ideas that are still undecided.

## Current implementation vs target architecture

| Area | Current | Target (documented) |
|------|---------|---------------------|
| Calculations | Named functions + flat input dicts | Same responsibility; richer FinancialInput/Result types may evolve |
| Persistence | None (sample JSON for demo only) | App Platform owns models/scenarios |
| Auth | None on the API yet | Service-to-service auth; no user JWT for DB/RLS |
| Data access | Caller supplies numbers | App Platform builds FinancialInput; this service never queries Supabase |

Protect the **target boundary** (do not add Supabase, user auth, or persistence here). Do **not** treat missing target components as a mandate to implement them in the current task unless explicitly requested.
