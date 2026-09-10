# Delivery bootstrap plan (execute in this repo)

Bring FarmBiddy FastAPI **process principles** into this service. Do **not** copy agent-server runtime (orchestrator, conversations, Redis, user JWT, RAG).

Principles source: sibling `rag-agent` (`.cursor/rules/07-fastapi-delivery.md`, `run_server.py`, lifespan, named venv). Domain source of truth remains this repo (`docs/architecture.md`, ADRs 0001–0002).

**Status:** Now list implemented in this repo (`api/` composition root, `run_server.py`, `/livez`, named-venv docs). Later items (Docker, `/readyz`, s2s auth) remain open. Do not land these files in `rag-agent`.

---

## Goal

This service should **start and ship like** agent-server, while still **calculating like** remote-functions:

- Named local venv
- Thin composition root + route module
- Two-phase boot (import cheap; lifespan marks ready)
- Dedicated process entry for non-reload runs
- Split liveness from “app is up”
- Calculation HTTP contract unchanged (`ok` / `needs_input` / `error`)

---

## Do not copy / do not add

| From agent-server | Why not |
|-------------------|---------|
| `api_server.py` wholesale | Overloaded composition root; wrong size |
| `require_user` / user JWT / Supabase | Violates ADR-0001 / ADR-0002 |
| Redis, turn locks, conversations | Out of scope (`docs/architecture.md`) |
| YAML config tree with empty environments | No settings to own yet |
| RequestContext / SmartOrchestrator | Stateless calcs; nothing to hold |
| Lifespan that “warms” formulas | Nothing to warm |

Service-to-service auth stays a **later** task (`docs/security.md`). When it lands, it belongs in `api/`, not `farm_functions/calcs/`.

---

## Now (execute this PR)

Keep the diff small. Prefer moving existing code over rewriting it.

1. **Named venv (docs + start hints only)**  
   Document as the default, matching agent-server style with prompt `remote-functions`:
   - Windows cmd / PowerShell / Unix activate snippets  
   - `python -m pip install -r requirements.txt` inside the venv  
   Update `README.md` Run section and `docs/development.md` Local setup.  
   Do not commit `.venv/`.

2. **Composition root vs routes**  
   - `api/app.py`: create `FastAPI(..., lifespan=lifespan)`, include router, nothing else.  
   - `api/routes.py` (new): health/livez, discovery, demo, `_register_function_routes` / example payloads.  
   Handlers still only call `run_function` / `list_functions`.

3. **Lifespan (empty but real)**  
   Startup: optional log line that the API is ready.  
   Shutdown: no-op (no pools).  
   Do not connect to network or load sample farm except on the demo route.

4. **Process entry**  
   Add `run_server.py`: dotenv optional if `.env` exists; `uvicorn.run("api.app:app", host=..., port=...)`.  
   Keep `python -m uvicorn api.app:app --reload` and `start.bat` for local reload.  
   Point `start.bat` at reload uvicorn (unchanged behaviour) or document both commands.

5. **Probes**  
   - `GET /livez` — process up, cheap (`{"ok": true}`).  
   - Keep `GET /health` as an alias of liveness **or** same body plus `version` from FastAPI app version. Do not ping calcs or disk.  
   - Skip `/readyz` until there is something to wait for (auth client, etc.).  
   Update `docs/api-contract.md` endpoint table and `tests/test_api.py`.

6. **Tests**  
   - Existing API tests still pass (import `app` from `api.app`).  
   - Add `GET /livez` smoke.  
   - No formula/test_calcs changes.

**Done when:** `python -m pytest` green; `python run_server.py` serves `/docs` and `/livez`; OpenAPI still lists per-function `/v1/functions/<key>/run` bodies; `farm_functions/calcs/` untouched.

---

## Later (not this PR)

- Multi-stage Dockerfile (`uv` venv, `CMD ["python", "run_server.py"]`, HEALTHCHECK on `/livez`)
- `/readyz` when startup actually waits on a dependency
- `DEPLOYMENT_ENVIRONMENT` + YAML only when there are real tunables (log level, timeouts, s2s)
- Structured `LIFECYCLE_EVENT` logs when deployed
- S2S auth in `api/` (still no user JWT)

---

## Files to touch (Now)

| File | Action |
|------|--------|
| `api/app.py` | Slim to app + lifespan + include_router |
| `api/routes.py` | New — current routes |
| `run_server.py` | New |
| `README.md` | Venv + run_server vs reload |
| `docs/development.md` | Venv default; pointer to this plan |
| `docs/api-contract.md` | `/livez` |
| `tests/test_api.py` | `/livez`; imports still work |
| `start.bat` | Comment or dual command; do not break Windows reload |

Do **not** change `farm_functions/calcs/`, schemas, rounding, or ADRs for this work.

---

## Execution (other team / later Agent)

Open **this** repository (`remote-functions`) as the workspace. Implement the **Now** list in one PR. Do not implement from a `rag-agent` tree except by absolute path into this repo.

Change-control: this does **not** change persistence, auth, or `needs_input`. No new ADR.
