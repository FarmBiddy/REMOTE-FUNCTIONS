# Multi-enterprise farms: what is analysed per enterprise and per farm

## Status

Accepted (design rules; implementation when a second enterprise, e.g. Sheep,
is added). Dairy remains the only enterprise until then.

## Context

Irish farms often run more than one enterprise (dairy + sheep, beef + sheep).
Analyses must work for one enterprise alone and for the whole farm, without
adding physically different things (litres + kg) or averaging ratios. Current
work must not block this.

## Decision

1. **Direct vs shared.** Income and **variable (direct) costs** belong to an
   enterprise. Fixed costs (labour, machinery, insurance, electricity, rent …)
   are **shared** at farm level unless the user supplies explicit allocation
   keys (%, hectares, livestock units). The Engine never invents an allocation.
2. **Enterprise view** = enterprise income − its variable costs =
   **gross margin**, plus enterprise physical KPIs. **Farm view** = Σ
   enterprise figures + shared items → Operating Surplus, net profit.
3. **What combines:**

   | Kind | Per enterprise | Farm |
   |---|---|---|
   | EUR amounts (income, costs, gross margin, surplus, cash lines) | yes | yes — sum of enterprises + shared |
   | Farm-only (cash position, balance sheet, net worth, loans, debt capacity, DSCR, drawings, tax, off-farm income, multi-year plan, bank report) | no | yes |
   | Physical and per-unit (litres, kg lamb / wool, c/L, €/kg MS, per cow / ewe, product-price break-evens) | yes | **never summed** |
   | Per hectare | with user land allocation | with total area |
   | Ratios / % (margins, returns) | yes | **recomputed from summed totals**, never averaged |
   | Shared fixed costs per enterprise | only with user allocation keys | yes |

4. **Drivers are enterprise-specific, impact is farm-level:** a milk-price or
   lamb-price shock is defined on its enterprise, but cash, DSCR and cash
   break-evens are measured on the farm. A farm tornado ranks drivers of all
   enterprises together.
5. **Response shape** (when multi-enterprise lands):
   `{enterprises: {<id>: {...}}, shared: {...}, farm: {...}}`; single-enterprise
   calls keep today's shapes.
6. **Already compatible:** loans, balance sheet, drawings, tax, debt capacity
   and reports are farm-level inputs today; the current Dairy P&L / KPI /
   sensitivity outputs become the Dairy enterprise view.

## Consequences

- New work keeps farm-level concepts out of enterprise packages and never
  averages ratios.
- Livestock units (for stocking rate and per-LU comparisons) will need a
  per-enterprise conversion table supplied with the enterprise profile.

## Related

ADR-0013, ADR-0016, ADR-0017, ADR-0025 (§6), ADR-0033
