# Architecture Decision Records

Accepted decisions for this repository. See `docs/development.md` for when to add a new ADR.

| ADR | Title |
|-----|-------|
| [0001](0001-financial-service-app-platform-boundary.md) | Financial Service / App Platform data boundary |
| [0002](0002-authentication-and-service-trust.md) | Authentication and service-to-service trust |
| [0003](0003-scenario-persistence-ownership.md) | Scenario and financial model persistence ownership |
| [0004](0004-needs-input-missing-shape.md) | `needs_input.missing` structured field entries |
| [0005](0005-bankers-rounding.md) | Banker's rounding for published P&L outputs |
| [0006](0006-numeric-precision-phase1.md) | Numeric precision for Phase 1 annual P&L (float internally) |
| [0007](0007-phase1-operating-surplus.md) | Phase 1 Operating Surplus and finance separation |
| [0008](0008-phase1-validation-independence.md) | Phase 1 structural validation and input independence |
| [0009](0009-canonical-operating-statement.md) | Canonical Phase 1 annual Operating Statement (`pl.summary`) |
| [0010](0010-phase1-provenance-boundary.md) | Phase 1 calculation provenance / explainability boundary |
| [0011](0011-phase1-input-override-simulation.md) | Phase 1 annual input-override simulation — *superseded by 0034* |
| [0012](0012-phase1-named-scenarios.md) | Phase 1 caller-defined named financial scenarios — *superseded by 0034* |
| [0013](0013-phase1-layer-ownership.md) | Phase 1 layer ownership (Dairy cost catalogue; land leasing) |
| [0014](0014-core-agriculture-boundaries.md) | Core and Agriculture package boundaries (L2 / L3) |
| [0015](0015-dairy-specialisation-boundary.md) | Dairy specialisation package boundary (L4) |
| [0016](0016-dairy-boundary-consolidation.md) | Dairy boundary consolidation (post-L4 gate) |
| [0017](0017-orchestration-canonical-resolution.md) | Application orchestration resolves canonical packages (L5) |
| [0018](0018-period-domain-contract.md) | Period domain contract (P1.1 monthly identity vs drivers) |
| [0019](0019-monthly-operating-statement-http.md) | Monthly Operating Statement HTTP contract (`pl.monthly`) |
| [0020](0020-multi-period-pnl-semantics.md) | Multi-period P&L semantics (P2.0; YTD / series compose monthly) |
| [0021](0021-multi-period-http.md) | Multi-period Operating Statement HTTP contract (`pl.months`; implemented P2.4) |
| [0022](0022-cash-flow-foundation.md) | Cash Flow foundation decisions (P3.0 / P3.1 contracts) |
| [0023](0023-shared-category-ids.md) | Shared category IDs across P&L and Cash Flow; cash catalogue declared once |
| [0024](0024-cash-position-roll-forward.md) | Opening / closing cash and consecutive multi-month roll-forward (`cf.months`) |
| [0025](0025-engine-scope-loans-forecast.md) | Engine scope for the platform prototype: loan amortisation (`loan.schedule`), forecast, enterprises |
| [0026](0026-seasonal-run-rate-forecast.md) | Seasonal run-rate forecast (`pl.forecast`, `cf.forecast`) |
| [0027](0027-nested-needs-input.md) | Nested `needs_input` with `missing[].path` |
| [0028](0028-dairy-kpis.md) | Dairy KPIs (`kpi.summary`): c/L, per cow, DSCR |
| [0029](0029-sensitivity-break-even.md) | Sensitivity scenarios and milk-price break-evens (`risk.sensitivity`) |
| [0030](0030-household-drawings.md) | Household drawings as a financing cash outflow |
| [0031](0031-investment-scenarios.md) | Investment scenarios in `risk.sensitivity` ("Can I afford it?"); per-scenario break-evens |
| [0032](0032-kpi-solids-hectare-debt.md) | KPIs per kg milk solids, per hectare and debt |
| [0033](0033-variable-fixed-costs-herd.md) | Variable / fixed costs, gross margin and herd-size scenarios |
| [0034](0034-remove-in-process-simulation.md) | Remove in-process annual simulation and named scenarios |
| [0035](0035-variance-analysis.md) | Variance analysis (`pl.compare`, `cf.compare`) |

## Not yet decided (candidates — do not invent ADRs until decided)

- Concrete service-to-service auth mechanism (API key, mTLS, signed tokens, etc.)
- Calculation / API versioning strategy beyond the existing `/v1` prefix
- Whether typed `FinancialInput` / `FinancialResult` become the **sole HTTP** surface (in-process types exist in `farm_functions/domain.py`; HTTP remains named functions + flat JSON; `pl.months` uses nested `months[]` per ADR-0021)
