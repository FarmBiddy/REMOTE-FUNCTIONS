# Service-to-service bearer token, readiness and safe binding

## Status

Accepted (dairy-ready). Chooses the mechanism left open by ADR-0002.

## Context

The engine will run locally first, then behind the Platform (the Figma
prototype site and its backend). Farm figures are private. ADR-0002 already
fixes the trust model: users log in to the Platform; the engine trusts the
Platform as a service and never sees user sessions.

## Decision

1. **Shared bearer key.** When `ENGINE_API_KEY` is set, every `/v1/...`
   request must send `Authorization: Bearer <key>`; otherwise HTTP 401 with
   `error.code: unauthorized`. Constant-time comparison. Probes (`/livez`,
   `/health`, `/readyz`), OpenAPI docs and CORS preflights stay open.
2. **Unset key = open, for local development only.** The app logs a warning.
   `run_server.py` reads `ENGINE_HOST` / `ENGINE_PORT` (default
   `127.0.0.1:8000`) and **refuses to start** on a non-loopback host without
   a key.
3. **Only the Platform backend holds the key.** Browsers never call the engine
   directly: Browser (user login) → Platform backend (checks the session, adds
   the key) → Engine. A key in browser code is a leaked key.
4. **`GET /readyz`**: 200 `{"ready": true}` after startup, 503 before startup
   and during shutdown, for deploy health checks.
5. The key lives in `.env` (git-ignored) or the host's secret store, never in
   the repo. Rotate by changing it in both places.

## Consequences

- No user login, sessions or farm ownership in the engine (ADR-0001/0002).
- Upgrade path when needed: signed short-lived service tokens (JWT) or mTLS,
  replacing only the middleware.
- Docker / hosting configuration is deferred until a host is chosen.
- HTTPS is required once the engine leaves localhost (host / proxy concern).

## Related

ADR-0001, ADR-0002, `docs/security.md`
