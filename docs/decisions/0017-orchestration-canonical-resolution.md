# Application orchestration resolves canonical packages (L5)

## Status

Accepted (L5 Orchestration / Composition Seam)

## Context

After L2–L4 and Dairy consolidation (ADR-0014–0016), formula ownership lived in
Core, Agriculture, and Dairy. Application modules (`registry`, `provenance`,
`domain`, loaders) still imported those capabilities through
`farm_functions.calcs` re-exports, which made the compatibility facade look like
the centre of the engine.

## Decision

1. **Application/orchestration imports canonical packages directly:**
   Dairy, Agriculture, and Core. Registry handlers, provenance, domain
   `calculate_annual_pnl`, and loaders must not import `farm_functions.calcs`.
2. **`calcs` (and `farm_functions.rounding`) remain a compatibility facade** for
   legacy/external imports and identity tests. They must not grow a second
   formula implementation.
3. **`registry.py` remains the public capability catalogue** plus thin publish
   wrappers. It is not split into a separate DI container or plugin registry.
   No dependency-injection framework or abstract base classes for this seam.
4. **Runner stays dispatch-only** (validate → look up catalogue → call handler).
5. **Provenance continues to call the same canonical formula functions**; it must
   not independently reimplement financial truth.

## Consequences

- HTTP and public calculation IDs are unchanged.
- Future enterprise specialisations (e.g. Beef) add a package + catalogue
  entries rather than rewriting the execution path or Core/Agriculture bodies.
- Import direction is characterised in `tests/test_layer_import_boundaries.py`.

## Related

- ADR-0014, ADR-0015, ADR-0016
- `docs/architecture.md` (Execution seam)
- `farm_functions/registry.py`, `runner.py`, `provenance.py`, `domain.py`
