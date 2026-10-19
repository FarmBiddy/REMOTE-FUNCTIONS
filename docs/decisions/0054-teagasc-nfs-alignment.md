# Teagasc National Farm Survey alignment (casual labour, family farm income)

## Status

Accepted (ie-tax). Extends ADR-0033 and ADR-0028.

## Context

Farmers and advisors compare a farm with the Teagasc National Farm Survey
(NFS): 2025 dairy total costs 35.03c/L and net margin 23.13c/L. The Engine
already splits variable and fixed costs the Profit Monitor way (ADR-0033), but
two NFS conventions differed: casual labour is a direct cost, and the NFS
headline is family farm income (after depreciation and interest), with dairy
costs per litre including depreciation.

## Decision

1. New operating cost line `casual_labour` (relief milkers, calving help):
   a **variable** cost. `labour` stays regular hired labour, a fixed cost.
   Optional, default 0, so existing calls are unchanged.
2. `kpi.summary` takes the period totals `pl.net` takes (`depreciation`,
   `interest`, livestock / stock opening and closing values) and, when
   `depreciation` is sent, returns `teagasc`:
   - whole farm: gross output (sales, grants, herd / stock value change),
     direct costs, overheads (fixed + depreciation + interest), **family farm
     income** = gross output − direct − overheads (equals `pl.net` net profit
     before tax);
   - dairy per litre: gross output without decoupled payments (schemes),
     direct costs, fixed costs incl. depreciation, total costs, net margin.
3. NFS benchmarks are Platform data, as with milk quality (ADR-0052); the
   Engine stores none.

## Consequences

- Depreciation is the farm's register (ADR-0037), not the NFS replacement-cost
  basis (machinery 10%, buildings 5% declining balance); the Platform says so.
- Whether NFS dairy "other fixed costs" include interest is not confirmed; the
  per-litre total costs here exclude it.

## Related

ADR-0028, ADR-0033, ADR-0037, ADR-0038, ADR-0052, ADR-0053
