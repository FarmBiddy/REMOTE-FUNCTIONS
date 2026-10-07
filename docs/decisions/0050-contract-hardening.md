# Contract hardening: limits, version meta, examples, naming

## Status

Accepted (dairy-ready)

## Context

A contract review before Dairy is declared complete found: malformed JSON
caused a server error; 11 of 30 IDs had empty OpenAPI examples; month lists
were unbounded; the Operating Surplus had three names (`profit.net`,
`operating_surplus`, `surplus`); responses carried no engine version for
report audit trails.

## Decision

1. **Malformed JSON** → `status: error`, `error.code: invalid_json`.
2. **Size limits:** month lists ≤ 120 items (`MAX_MONTHS`, 10 years);
   per-year assumption lists ≤ 10. Every input list has a bound; a test fails
   if any list of any ID is unbounded. Hosts should also cap the request body
   size at the proxy.
3. **`meta.engine_version`** on every `run` envelope (`ok`, `needs_input`,
   `error`), from `farm_functions/version.py` (`1.0.0` = Dairy complete). Bump
   it whenever published figures or response shapes change.
4. **Naming:** the Operating Surplus is `operating_surplus` in every
   post-Phase-1 output (`kpi.summary`, `debt.capacity`, `risk.sensitivity`,
   `risk.tornado`, including `rank_by`). `profit.net` stays in the Phase 1
   statements (`pl.*`, ADR-0007) as the same quantity.
5. **HTTP status policy** (documented, unchanged): calculation routes answer
   **200** with the outcome in `status` (`ok` / `needs_input` / `error`);
   transport-level problems use HTTP codes: 401 (`unauthorized`, ADR-0049),
   404 (unknown ID on discovery).
6. **Examples:** one real payload per ID (Joe Bloggs' farm) in
   `sample_data/examples/<id>.json`, published as the OpenAPI example and
   run by a test so it never goes stale. Regenerate from
   `tests/test_end_to_end_joe.py` payloads after contract changes.

## Consequences

- `surplus` → `operating_surplus` is a breaking rename for the Platform
  (announced with this change).
- Typed response schemas: ADR-0051.

## Related

ADR-0004, ADR-0007, ADR-0048, ADR-0049
