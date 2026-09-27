# Multi-period P&L semantics (P2.0)

## Status

Accepted (P2.0 semantics audit — no multi-period calculation implementation yet)

## Context

Annual `pl.summary` and monthly `pl.monthly` are integrated with the Mock
Platform. Platform still mocks YTD totals and Jan–Dec actual charts. Near-term
Engine scope is frozen to **Operating Statements (P&L)**, then later **Cash
Flow** — not balance sheet, tax, depreciation, forecasting, KPIs, advice, or
database integration.

P2 must support three surfaces without a second P&L engine:

1. Multiple explicit months
2. YTD Operating Statement
3. Jan–Dec actual series

Constraints already locked by ADR-0018 / ADR-0019 / P1.3:

- Compose existing monthly capability; do not invent months
- No annual ÷ 12
- No forecast fill
- No averaging of monthly margins to produce YTD margin
- Keep `pl.summary` and `pl.monthly` compatible

## Decision

### Scope freeze

1. Near-term Engine product focus: P&L Operating Statements, then Cash Flow.
2. Out of scope for this phase: balance sheet, tax, depreciation, full
   accounting, benchmarking, recommendations, AI advice, Monte Carlo,
   sensitivity, forecasting, KPI frameworks, persistence/auth/DB,
   tokenisation, and FarmBiddy retrieval architecture.

### D1 — YTD window identity

A YTD statement is identified by `kind: ytd`, `year`, `as_of_month` (1–12),
**and** an explicit list of monthly inputs for every month included. The
result records `months_included` (sorted). The Engine must **not** invent
Jan…as_of months when inputs are missing.

### D2 — Incomplete / gapped months

- **Series (Jan–Dec chart):** Sparse months allowed. Return only months
  provided; Platform may chart null/gap for missing months. Never synthesise
  a missing month.
- **Named YTD through month M:** Require contiguous January…`as_of_month`
  all present, or reject with a structured error. Do not silently compute a
  partial window under a “through March” label.

### D3 — Explicit zero vs omitted month

Omitted month ≠ zero month. A provided month with all-zero drivers is a valid
actual (zero activity). Omission means “no actuals for this month.”

### D4 — YTD / multi-month aggregation maths

1. Run the existing monthly Operating Statement for each included month.
2. YTD operating income = sum of monthly operating-income totals (full
   precision before publish).
3. YTD operating costs = sum of monthly operating-cost totals.
4. YTD Operating Surplus = Core `net_profit(ytd_income, ytd_costs)`.
5. YTD margin = Core margin on **YTD income and YTD costs** — never the
   average of monthly `margin_pct`.
6. YTD `finance.loan_repayments` = sum of monthly finance amounts; remains
   outside Operating Surplus and margin.
7. Publish with existing banker's rounding once on YTD aggregates.

### D5 — Relationship to annual `pl.summary`

YTD and annual remain **independent**. No forced rule that YTD(December)
equals `pl.summary`. Annual milk drivers differ from monthly. Consistency of
source data is an App Platform / Agent concern, not an Engine reconciliation
rule in P2.

### D6 — YTD publication shape (keep basic)

YTD publishes the same aggregate nests as monthly (`revenue` / `costs.total` /
`profit` / `finance`). Summing `costs.lines` by catalogue key is deferred
until a Platform need requires it.

### D7 — Smallest architecture

| Layer | Responsibility |
|-------|----------------|
| Core / Agriculture / Dairy monthly | Unchanged single-month primitives |
| Domain | Composition only: list of monthly envelopes → monthly results → optional YTD aggregate |
| Application / API (P2.4) | Prefer one multi-period HTTP ID (e.g. `pl.months`) returning `months[]` and/or `ytd`; keep `pl.monthly` and `pl.summary` |

Forbidden: a second P&L formula package; Core “period engine”; inventing twelve
monthly calls; Platform as the official owner of YTD maths.

### D8 — Ownership boundary

| Concern | Owner |
|---------|-------|
| Which months exist / are complete | App Platform / Agent |
| Monthly OS maths | Financial Engine |
| YTD / series composition maths | Financial Engine (Domain) |
| Forecast, loan cards, suppliers, events, farm ID | Platform |
| Persistence of monthly actuals | Platform (Engine stays stateless) |

## Consequences

- **P2.0** records semantics only (this ADR). No registry/HTTP/code yet.
- **P2.1** — multi-month list → list of monthly results.
- **P2.2** — YTD aggregate (D1–D4) + characterisation tests.
- **P2.3** — Jan–Dec series shape (sparse OK).
- **P2.4** — HTTP / external contract; annual and single-month unchanged.
- **I6** — Mock Platform wires YTD + actual chart series; forecast stays mock.

## Related

- ADR-0018 (period Domain contract)
- ADR-0019 (`pl.monthly` HTTP)
- ADR-0007 (Operating Surplus / finance)
- ADR-0009 (canonical annual `pl.summary`)
- `docs/architecture.md`, `docs/domain-model.md`
