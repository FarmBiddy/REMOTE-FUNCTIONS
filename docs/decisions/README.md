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

## Not yet decided (candidates — do not invent ADRs until decided)

- Concrete service-to-service auth mechanism (API key, mTLS, signed tokens, etc.)
- Calculation / API versioning strategy beyond the existing `/v1` prefix
- Whether typed `FinancialInput` / `FinancialResult` become the **sole HTTP** surface (in-process types exist in `farm_functions/domain.py`; HTTP remains named functions + flat JSON)
