# Multi-period Operating Statement HTTP contract (`pl.months`)

## Status

Accepted and implemented (P2.4 — public ID `pl.months` live in catalogue / HTTP)

## Context

P2.1 provides in-process multi-month Domain composition
(`calculate_multi_month_dairy_statements`). P2.2 provides in-process YTD
aggregation (`calculate_ytd_dairy_statement`) from contiguous January through
`as_of_month`. ADR-0020 (D7) prefers one multi-period HTTP ID returning
`months[]` and/or `ytd`, while keeping `pl.summary` and `pl.monthly`.

The Mock Platform needs a single call that returns chronological monthly
Operating Statements (for Jan–Dec actual charts) and optionally a YTD
Operating Statement, without calculating P&L in JavaScript and without twelve
`pl.monthly` calls.

## Decision

### D1 — Public ID

**`pl.months`** — additive catalogue ID. Path:
`POST /v1/functions/pl.months/run`. Does **not** replace `pl.monthly` or
`pl.summary`. A separate `pl.ytd` ID is not required.

### D2 — Request transport

Nested JSON (first intentional nest under the runner):

- **`months`** (required): non-empty array. Each element has the same fields as
  `pl.monthly` (`year`, `month`, `milk_litres`, `milk_price`, optional drivers
  omit → `0`). Unknown keys forbidden.
- **`ytd`** (optional): object `{ year, as_of_month }` when YTD is requested;
  omit or JSON `null` when not. Not top-level `year` / `as_of_month` (avoids
  colliding with per-month period identity).

Forbidden on the request: chart coordinates, forecast values, UI labels,
colours, farm IDs, supplier/event payloads. Currency is not a request field
(EUR default, as today).

### D3 — Success response

Envelope unchanged: `{ status: "ok", function: "pl.months", result }`.

```text
result = {
  currency: "EUR",
  months: [ MonthlyDairyStatementResult, ... ],  // chronological
  ytd: YtdDairyStatementResult | null
}
```

- Serialize Domain dumps unchanged (`model_dump()`); no response DTOs.
- Always include the `ytd` key; value `null` when YTD was not requested.
- Bundle `currency` from the multi-month Domain result; per-statement
  `currency` retained as Domain publishes it.

### D4 — Domain mapping (no new maths)

| HTTP | Domain |
|------|--------|
| Each month item | Same peel as `pl.monthly` → `MonthlyDairyStatementModel` |
| Full `months` list | `MultiMonthDairyStatementModel` → `calculate_multi_month_dairy_statements` |
| Optional `ytd` + same envelopes | `YtdDairyStatementModel` → `calculate_ytd_dairy_statement` |

HTTP must not weaken Domain rules: sparse/cross-year OK without YTD; YTD
requires contiguous January…`as_of_month` for one year; months after
`as_of_month` ignored for YTD; wrong-year months rejected; duplicates
rejected; omitted month ≠ zero; YTD margin from YTD totals via Core; loans
outside Operating Surplus.

### D5 — Jan–Dec actual series

P2.1 + `result.months` fully satisfies the Jan–Dec actual financial series.
No chart-series Domain type. Platform plots from
`period.month` / `revenue.total` / `costs.total` / `profit.net`. Engine never
invents missing months.

### D6 — Errors

Reuse existing statuses and codes. **No new error-code taxonomy.** P2.4 must
extend `map_validation_error` for nested/`value_error` cases so the runner does
not crash on unmapped Pydantic types.

| Failure | Status | `error.code` | `details.reason` (when used) |
|---------|--------|--------------|------------------------------|
| Missing top-level `months` | `needs_input` | `missing_required` | — |
| `months: []` | `error` | `invalid_type` | `empty_months` |
| Duplicate `{year,month}` | `error` | `invalid_type` | `duplicate_period` |
| Nested missing required driver | `error` | `missing_required` | — (not `needs_input`; runner only scans top-level) |
| Nested null / negative / non-finite / bad type | `error` | existing codes | — |
| Invalid calendar `year` / `month` / `as_of_month` | `error` | `invalid_type` | — |
| YTD gap / missing January | `error` | `invalid_type` | `ytd_incomplete` |
| YTD wrong-year month | `error` | `invalid_type` | `ytd_year_mismatch` |
| Unknown field | `error` | `unknown_field` | — |

Branch on `error.code` (and `details.reason` for period-set structure), not
message text.

### D7 — Compatibility and layers

- `pl.summary` and `pl.monthly` request/response behaviour unchanged.
- Discovery gains `pl.months` with `required: ["months"]`, `optional: ["ytd"]`
  (nested month field names are documented in `integration-external.md`, not
  listed in discovery).
- Application/registry: assemble + serialize only; no financial formulas in
  routes or handlers.
- Annual and March monthly reference totals remain the locked smoke values.

## Consequences

- **P2.3** froze this contract in documentation.
- **P2.4** implemented the thin adapter: `PlMonthsInput` → registry
  `_handle_pl_months` → P2.1 → optional P2.2 → Domain dumps; runner allows
  null on optional `ytd` and maps handler `ValidationError`;
  `tests/test_pl_months_http.py`.
- Mock Platform (I6) can wire charts and YTD from one Engine call.
- ADR-0019 note that future YTD might use `pl.ytd` is superseded for the
  multi-period surface by this single-ID decision.

## Related

- ADR-0020 (multi-period P&L semantics)
- ADR-0019 (`pl.monthly` HTTP)
- ADR-0018 (period Domain contract)
- `docs/integration-external.md`, `docs/api-contract.md`, `docs/domain-model.md`
