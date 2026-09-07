# ADR-0002: Authentication and service-to-service trust

## Status

Accepted (trust model). Concrete s2s mechanism (API key, mTLS, etc.) is **not** decided yet.

## Context

User authentication and Supabase sessions are owned by the App Platform. Forwarding a user JWT into the Financial Service so it can call Supabase/RLS would collapse the data boundary (see ADR-0001).

## Decision

- User authentication remains at the App Platform.
- The Financial Service **MUST NOT** receive a user JWT for the purpose of accessing Supabase or enforcing farm ownership.
- When authentication is added to this service, it will be **service-to-service** trust between App Platform and Financial Service.
- The Financial Service trusts the authenticated upstream service, not the end-user's Supabase session.

## Consequences

- Do not implement user login, session cookies, or RLS checks here.
- Adding auth later must choose and document a specific s2s mechanism without changing this trust model unless a new ADR supersedes it.
- Absence of auth in the current API does not weaken this decision.

## References

- `docs/security.md`
- `docs/architecture.md` (Authentication)
