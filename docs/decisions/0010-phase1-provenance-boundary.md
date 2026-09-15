# Phase 1 calculation provenance / explainability boundary

## Status

Accepted (Workstream B6)

## Context

Phase 1 already provides deterministic calculation evidence via
`explain_annual_pnl` for seven atomic annual P&L calculations. `pl.summary` is the
canonical Operating Statement (ADR-0009). Without a clear assembly contract, a later
API/platform/agent layer might invent a second calculator, duplicate `pl.summary`
provenance, put conversational AI inside this service, or assume HTTP explain
endpoints exist.

## Decision

1. **In-process calculation evidence:** Phase 1 provenance is deterministic structured
   evidence produced by `explain_annual_pnl`. It records calculation ID, inputs used,
   formula/operation metadata, value, and unit for:
   `revenue.milk`, `revenue.schemes`, `revenue.other`, `revenue.total`, `costs.total`,
   `profit.net`, `profit.margin`. Values come from the existing calculation functions
   (no second financial engine).
2. **Canonical statement:** `pl.summary` remains the authoritative combined annual
   Operating Statement. It does **not** receive a separate duplicated provenance
   object. Explain its operating lines via the seven component provenance records for
   the same drivers.
3. **Finance:** `loan_repayments` is read from `pl.summary` / `FinancialResult.finance`.
   It is finance/debt on the statement, not an Operating Surplus provenance input.
4. **Labels:** Human-readable financial meaning comes from catalogue descriptions and
   documented semantics (ADR-0007 / ADR-0009). Stable IDs are retained:
   `profit.net` → Operating Surplus; `profit.margin` → Operating Surplus Margin.
5. **Precision:** Provenance may be unrounded; published aggregates remain authoritative
   (ADR-0005 / ADR-0006).
6. **HTTP:** Provenance is not on Phase 1 HTTP calculation responses and there is no
   `/explain` endpoint in this workstream.
7. **Engine vs agent:** Natural-language explanation, advice, and conversational
   presentation belong to a future agent/platform layer — not this financial service.

## Consequences

- Another layer can answer “Why is Operating Surplus €77,000?” using deterministic
  evidence (e.g. €240,000 − €163,000) without recalculating or guessing.
- Avoids duplicated financial maths, a second explainability engine, mixing AI
  commentary into the calculator, and unnecessary API expansion in B6.
- Characterisation of provenance behaviour remains in existing provenance / precision /
  surplus tests; B6 is primarily a documentation/architecture record.

## Related

- `docs/domain-model.md`, `docs/api-contract.md`
- ADR-0005, ADR-0006, ADR-0007, ADR-0009
- `farm_functions/provenance.py`, `farm_functions/registry.py`
