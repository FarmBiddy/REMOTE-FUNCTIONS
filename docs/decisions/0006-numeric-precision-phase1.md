# ADR-0006: Numeric precision for Phase 1 annual P&L

## Status

Accepted

## Context

Annual P&L formulas use IEEE-754 binary floating-point. Publication rounding is already defined in ADR-0005. Callers and future modules need an explicit policy for:

- internal numeric type
- whether intermediate business rounding is allowed
- how precision differs from publication rounding
- when a Decimal / fixed-point migration should be reconsidered

This service currently performs simple annual multiplication, addition, subtraction, and ratios. It does not run ledgers, tax engines, payment rails, loan amortisation, multi-period compounding, or statutory accounting journals.

Characterisation showed binary-float artefacts (for example `0.1 + 0.2`) are contained by publish-time banker's rounding for the current public contract. No Phase 1 published-output failure requiring Decimal migration was demonstrated.

## Decision

**Keep float for the current Phase 1 annual P&L engine.**

- Validated calculation inputs are stored as Python `float` (`NonNegativeNumber`; ints are promoted; bools, strings, null, NaN, and infinity are rejected).
- Formulas in `farm_functions/calcs/` use full available float precision with **no intermediate business rounding**.
- Publication uses ADR-0005 helpers (`round_money`, `round_margin_ratio`, `round_margin_pct`): Decimal quantize with round half to even, then return `float`.
- Aggregate totals are computed from underlying (full-precision) values and rounded **once** at publication.
- Independently rounded line items are **presentation** values; they are not required to re-sum exactly to the published aggregate. Published aggregate totals are **authoritative**.
- Provenance (`explain_annual_pnl`) retains unrounded calculated values.
- Decimal / fixed-point migration is **deferred** until a use case requires stronger decimal guarantees.

### Precision vs rounding

- **Precision** — how accurately a number is represented internally (binary float may not store `0.1` exactly).
- **Rounding** — how FarmBiddy publishes a value for the contract (for example money to 2 decimal places).

These are separate concerns. Do not treat publish rounding as a substitute for a future ledger-grade numeric type if requirements change.

### Reassessment triggers

Reconsider Decimal or fixed-point (for example integer cents) when any of the following become in-scope:

- accounting ledger / journal posting
- tax calculations
- payment processing
- loan amortisation schedules
- cent-exact reconciliation requirements
- multi-period compounding
- statutory reporting
- external accounting integrations

A Decimal rewrite is a separate approved task; it must not be introduced as a silent local convenience.

## Consequences

- Published outputs and formulas remain unchanged by this ADR.
- Integrations must treat published aggregate totals as authoritative (see ADR-0005 and `docs/api-contract.md`).
- Characterisation tests in `tests/test_precision_policy.py` protect the documented behaviour.

## References

- ADR-0005 (banker's rounding for published outputs)
- `farm_functions/rounding.py`
- `farm_functions/schemas.py` (`NonNegativeNumber`)
- `docs/domain-model.md` (Rounding / precision)
- `tests/test_precision_policy.py`
