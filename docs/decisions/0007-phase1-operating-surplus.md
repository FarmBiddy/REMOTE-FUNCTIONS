# Phase 1 Operating Surplus and finance separation

## Status

Accepted (Workstream B2)

## Context

The annual dairy P&L previously summed loan repayments into `costs.total` and labelled
`profit.net` as net profit. That mixed operating performance with debt service and
over-claimed full accounting profit.

B1 approved Phase 1 semantics: headline **Operating Surplus**, livestock gross sales,
paid labour only, operating-only other income/grants, and milk = cows × sold litres ×
average EUR/litre. B2 implements those rules in the calculation engine.

## Decision

1. **Headline:** Phase 1 main result is Operating Surplus =
   Operating Income − Operating Costs. Public IDs `profit.net` and `profit.margin`
   stay; their Phase 1 meaning is Operating Surplus / Operating Surplus margin.
2. **Finance:** `loan_repayments` is debt service, not an operating cost. It does not
   reduce Operating Surplus. It is retained on `pl.summary` / `FinancialResult` under
   `finance.loan_repayments`. Principal vs interest is not split in Phase 1.
3. **Operating cost catalogue:** Authoritative list is `OPERATING_COST_CATEGORIES` in
   `farm_functions/calcs/costs.py`. Phase 1 includes existing operating lines plus
   `repairs_maintenance`, `rent_lease`, `professional_fees`, `levies`,
   `other_operating_costs`. Adding a later operating cost extends that catalogue plus
   aligned schema/metadata/`CostLines`/loader keys — no engine redesign.
4. **HTTP:** Request bodies remain flat JSON. Response nesting for `pl.summary` gains
   `finance`; `costs.lines` contains operating lines only.
5. **Limitations (explicit):** Not full accounting net profit. Excludes depreciation,
   tax, drawings, capex, livestock purchases/herd valuation, unpaid family labour.

## Consequences

- Intentional contract change: sample/reference Operating Surplus moves from €65,000 to
  €77,000 when loans (€12,000) leave operating costs and no new cost lines are populated.
- `costs.total` (named calculation and `pl.summary.costs.total`) is operating-only.
- Callers that treated `profit.net` as post-debt profit must be updated.
- Golden/reference cases updated deliberately under this ADR.

## Related

- `docs/api-contract.md`, `docs/domain-model.md`
- `farm_functions/calcs/costs.py`, `farm_functions/calcs/summary.py`, `farm_functions/domain.py`
