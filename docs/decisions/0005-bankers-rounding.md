# ADR-0005: Banker's rounding for published P&L outputs

## Status

Accepted

## Context

Annual P&L formulas use IEEE-754 floats and did not document how results are rounded for the API. Python 3 `round()` happens to use round-half-to-even, but that was an implementation accident, not a stated principle.

Callers (UI, agent, reports) need a stable, named rule for money and margin display.

## Decision

- **Formulas stay full precision** in `farm_functions/calcs/`.
- **Published outputs** (HTTP `ok` results, `pl.summary`, registry money wrappers) use **banker's rounding** (round half to even) via `farm_functions/rounding.py`.
- Money and `margin_pct`: 2 decimal places.
- `profit.margin` (0–1 ratio): 4 decimal places.
- Totals are rounded **after** summing at full precision, not by summing already-rounded lines.
- Provenance (`explain_annual_pnl`) reports unrounded formula values unless a later task changes that.

## Consequences

- Half-unit cases (for example 1.225 to 2 dp) go to the even neighbour (1.22), not always away from zero or always up.
- Do not call raw `round()` for P&L output; use `round_money` / `round_margin_ratio` / `round_margin_pct`.

## References

- `docs/domain-model.md` (Rounding)
- `farm_functions/rounding.py`
