# Irish rules layer: tax estimates by jurisdiction (`farm_functions.ie`)

## Status

Accepted (ie-tax, design; implemented in phases below). Narrows the "Engine
does not compute tax" scope of ADR-0006, ADR-0036 §4, ADR-0037, ADR-0038 §5,
ADR-0042 and ADR-0046 for Irish farms. Rules and sources: `docs/ie-rules.md`.

## Context

Every money result today stops before tax: `tax` is a caller-supplied number
in `debt.capacity` and `plan.projection`, and VAT is out of scope. Irish
farmers' real position depends on rules the Engine could apply: the flat-rate
VAT addition on milk and cattle sales, stock relief, capital allowances, income
averaging, income tax / USC / PRSI or corporation tax, and partnership splits.
These rules change every Budget (the flat-rate addition was 5.1% in 2025, 4.5%
in 2026, 4.8% announced for 2027), so they must be dated, sourced data, not
constants. Farms may trade as sole traders, registered partnerships or
companies; all three must be covered. FarmBiddy may later expand to other
countries.

## Decision

1. **Jurisdiction package `farm_functions/ie/`.** It owns Irish rules (tables
   and the formulas that apply them). Dependency: Application → `ie` →
   Agriculture / Core. Core, Agriculture and Dairy never import `ie`;
   enterprise packages stay country-neutral (EU law already in Dairy, e.g.
   ADR-0052 hygiene limits, stays there). No generic country interface until a
   second country exists; that country gets its own package and the shared
   shape is extracted then.
2. **Rules are dated, sourced data.** Each rule value carries `from`, `to`,
   `legal_ref`, `source` and `status` (`enacted` | `announced`). Lookup is by
   date or tax year. A date with no rule is an error (`rule_not_available`);
   the Engine never extrapolates a rate. Results using an `announced` rule say
   so. **One exception, projections:** `plan.projection` years after the last
   tax year with rules use that year's rules unchanged and say so
   (`rules_basis: latest_held_constant`). This is the usual planning
   assumption, not a forecast of future Budgets.
3. **Estimates, not returns.** Irish outputs carry `jurisdiction: "IE"`,
   `tax_year` and `rules_applied: [{rule_id, value, status}]`. A tax figure
   sent by the caller (the accountant's number) always wins over the estimate;
   existing `tax` inputs keep working unchanged.
4. **Business type is an input:** `sole_trader | partnership | company`.
   - Sole trader / partner: income tax, USC, PRSI Class S; general, YTF or RFP
     stock relief; income averaging; SFP credit.
   - Company: corporation tax 12.5% trading / 25% non-trading, general stock
     relief only, no averaging. Taking money out (salary, dividends, close
     company surcharge) is a separate phase.
   - Partnership: profit split by the profit-sharing ratio, then each partner
     as an individual. Builds on ADR-0047 (farm-level items).
5. **Person inputs only where a rule needs them** (YTF first year, marital
   status / assessment, other income, young farmer State aid already used).
   They are Platform data passed per call, never stored; history such as the
   €100,000 lifetime aid ledger or prior years' profits for averaging is an
   input.
6. **Modelling rules** (detail in `docs/ie-rules.md`):
   - Flat-rate addition on the gross price of agricultural sales for
     unregistered farmers; registered farmers' revenue is net of VAT.
   - Stock relief = rate × increase in trading stock (the `pl.net` livestock
     and stock changes), never creating or increasing a loss; caps applied as
     tax value.
   - Capital allowances are a tax schedule beside accounting depreciation
     (ADR-0037), on cost net of grants.
   - Capital grants are never income; scheme payments are trading income.
7. **Phases** (each its own commits and tests):
   1. VAT basis and flat-rate addition.
   2. Stock relief.
   3. Capital allowances schedule.
   4. Tax estimate (`tax.estimate`): income tax with joint assessment for
      married couples, USC / PRSI per person, or corporation tax; stock relief
      caps on tax saved. Its `total_tax` is passed as `debt.capacity` `tax`
      (composition, like `pl.net`).
   5. Tax per year in `plan.projection` from a `tax_profile` (instead of
      `assumptions.tax`, never both): herd value change as taxable trading
      stock with stock relief, capital allowances on the register, and income
      averaging over the Platform's `prior_farming_profits` then projected
      years (`insufficient_history` until 5 years are known). The Engine keeps
      no history between calls.
   6. Partnerships (`tax.partnership`): profit and stock increase split by
      profit share, relief and succession credit per partner, each partner's
      own estimate. An ownership split, so it does not wait for ADR-0047
      (enterprise split).
   7. Company extraction (`tax.company_extraction`): one salary / dividend mix
      per call through company tax, DWT, close company surcharge and the
      director's tax to household income after tax. The Platform compares
      mixes; choosing one is advice, not Engine work.
   Alongside (done, ADR-0054): align KPI definitions with Teagasc NFS terms (gross output,
   direct / overhead costs, family farm income) where they differ.
8. **Rule maintenance:** after each Finance Act, `docs/ie-rules.md` and the
   tables are updated together; tests pin one known case per tax year.

## Consequences

- The Engine now holds legal rates; it still holds no market opinions
  (prices, inflation, scenarios stay Platform-owned).
- README / api-contract "VAT and tax out of scope" lines change as phases land.
- Not included: CGT, CAT, stamp duty, VAT returns for registered farmers,
  payroll, pensions, compulsory disposal and carbon-tax diesel relief (later if
  needed), other countries.

## Related

ADR-0013, ADR-0014, ADR-0033, ADR-0036, ADR-0037, ADR-0038, ADR-0042,
ADR-0047
