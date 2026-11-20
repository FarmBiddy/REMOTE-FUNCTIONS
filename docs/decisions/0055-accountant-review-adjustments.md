# Accountant review adjustments (Irish dairy farms)

## Status

Accepted (accountant-review). Extends ADR-0053. Each numbered section below is
one change on the branch, added with the commit that makes it.

## Context

A retired IFAC farm accountant answered 12 questions on how Irish dairy farm
accounts, tax and loan applications work in practice (Nov 2026). Her answers,
checked against Revenue and statute (sources in `docs/ie-rules.md`), showed
where the Engine's Irish layer differs from practice.

## Decisions

### 1. Income averaging in `tax.estimate`; conditional needs_input

- "Nearly everyone is in income averaging." `tax.estimate` had no averaging,
  so an estimate for a farmer in averaging was silently on the actual year.
- Individuals (sole traders, partners) must now answer `income_averaging`;
  missing → `needs_input` (no default: a default would be a guess).
  Companies never average and do not send it.
- With averaging on, `prior_farming_profits` (the previous 4 years, oldest
  first, before capital allowances, after stock relief) and this year's
  `capital_allowances` (the amount already in `taxable_profit`) are needed.
  Assessable profit = average of the 5 profits before allowances − this
  year's allowances (s.657); USC and PRSI follow it. This year's stock relief
  counts a fifth towards its cap, as in `plan.projection`.
- The averaging period is a dated rule (`income_averaging_years`, 5,
  TCA s.657) in `farm_functions/ie/averaging.py`, listed in `rules_applied`.
- Runner: a model validator can raise `missing_inputs(...)` for fields that
  are required only in some cases; the runner answers `needs_input` with each
  field's full path (also inside nested models), as for ADR-0027.
- `tax.estimate` results gain `averaging` (`null` when off). Partner rows in
  `tax.partnership` carry the same key.

### 1b. Income averaging per partner in `tax.partnership`

- Each partner answers `income_averaging` (`partners[i].income_averaging` →
  `needs_input` when missing) and, if in averaging, sends their own share of
  the previous 4 years (`prior_farming_profits`, before allowances, after
  stock relief). Shares can change between years, so the history is theirs,
  not the partnership's split.
- When any partner averages, the partnership's `capital_allowances` is
  needed; each partner's share is deducted after averaging. The succession
  credit is limited by the partner's assessable (averaged) profit.
- `plan.projection` partners keep the profile-level averaging flag (their
  history is the profile's split by share): a separate input model, unchanged.

### 1c. `plan.projection`: averaging answer required, one rule

- `tax_profile.income_averaging` has no default for individuals any more
  (`needs_input` at `tax_profile.income_averaging`); companies leave it unset.
- The projection reads the averaging period from `income_averaging_years`
  (same rule as `tax.estimate`), so a change in law is one edit. Figures are
  unchanged.

### 2a. `tax_payments` cash line

- Tax time (31 October, or the ROS date in mid-November) is the farm's
  largest single payment and causes cash problems, mostly after a good year
  followed by a bad one. The monthly cash flow had no line for it.
- New financing outflow `tax_payments`, next to `household_drawings`: the
  gross amount paid to Revenue in the month (preliminary tax plus last year's
  balance). Cash only, never on the P&L (`pl.*` rejects it). Optional, 0 by
  default, so existing calls are unchanged.
- `cf.forecast` does **not** project it from last year: scaling one payment a
  year by a run-rate would be a guess. The Platform sends the expected
  payment (from `tax.payments`) and labels it approximate.

### 2b. `tax.payments`: preliminary tax and the pay date

- New ID. From this year's total tax (estimate or the accountant's figure),
  last year's (and the preliminary paid for it) and optionally the year
  before's, it returns the three safe-harbour options, the lowest safe
  amount, last year's balance and the **gross** total due on 31 October (and
  the ROS date where Revenue announced one).
- The Platform chooses `preliminary_basis` (required): the Engine has no
  opinion on which basis a farmer uses; it shows which one is lowest.
- Direct debit: equal monthly instalments from the start month to December
  (cents in December); only last year's balance is then due on the pay date.
- An overpayment of last year is reported, never netted against this year.
- This year's tax against the preliminary (settled with next year's return) is
  also split into `balance_due` / `overpaid` (review fix: it was one signed
  figure).
- Rules (90 / 100 / 105%) and ROS dates live in `farm_functions/ie/preliminary.py`.

### 2c. `plan.projection`: tax paid on the Irish dates

- With a tax profile, an individual's projection year no longer pays its own
  tax in the same year. It pays on the October inside it (31 October): the
  preliminary tax for that calendar year plus the year before's balance.
  For a calendar year end that is this year's preliminary + last year's
  balance; for a March or September year end the October falls in the plan
  year before the tax year ends, so it pays the previous tax year's.
- New profile inputs (individuals, required → `needs_input`):
  `preliminary_basis` (`current_90` | `prior_100`; the 105% direct debit
  basis stays in `tax.payments`, because a nil year inside a plan would leave
  the Engine choosing another basis) and `tax_history` (the tax years before
  the plan that the first pay date needs; the validator names them). A
  `preliminary_paid` for a year paid inside the plan is refused, not silently
  replaced (review fix).
- Outputs: `cash.tax` = paid in the year, `cash.tax_refund` = an overpaid
  balance coming back (gross, not netted), `balance_sheet.tax_owed` = accrued
  and unpaid (deducted in net worth), `tax.payments` per year. Repayment
  cover stays on the year's own tax: what the year's income owes.
- Companies and `assumptions.tax` are unchanged (paid in the year);
  corporation tax payment dates are in the backlog.

### 3. Flat-rate VAT addition as farm income

- The accountant: the flat-rate addition (FRA) on milk and cattle sales is
  farm income in the accounts and the tax computation. The Engine's P&L was
  ex-FRA and added it only in the tax bridge and the projection, so a
  management P&L understated income by the FRA (4.5% of sales in 2026) and a
  Platform passing the accountant's profit to the bridge counted it twice.
- New optional monthly line `flat_rate_addition` on `pl.*` (published inside
  `revenue.other`, so response shapes are unchanged) and on `cf.*` (operating
  inflow). The Platform fills it from `vat.flat_rate`: the Irish rate stays in
  the `ie` layer; Dairy only adds the amount.
- `tax.capital_allowances` no longer takes `flat_rate_addition`: it reaches
  taxable profit once, through `pl.net`.
- `risk.sensitivity` moves it in proportion to milk and cattle sales; it is not
  a tornado driver. `plan.projection` carries a base-year FRA in proportion to
  sales without a tax profile; with one the Engine computes it, so base months
  or `assumptions.lines_amount` carrying it are refused (`fra_conflict`).
  Investments cannot set it and `lines_pct` cannot shock it (it follows sales;
  found in the branch review, where a `lines_amount` next to a tax profile was
  counted twice).
- Annual Phase 1 IDs (`pl.summary`, `revenue.*`) are unchanged (ex-FRA).
- Whether Teagasc NFS figures are VAT-inclusive is unconfirmed (likely).

### 4. Filed figures and the tax source for lending

- The accountant: loan approval looks at the last 3 years' filed returns
  (AIB and Bank of Ireland application forms confirm: 2–3 years of accounts
  and Form 11 / assessments). `debt.capacity` only used the months sent.
- `filed_years` (≤ 3: net profit, depreciation, interest, total tax from the
  filed accounts and returns) adds a `filed` view: the average surplus before
  finance (net profit + depreciation + interest, comparable with the operating
  surplus), the average tax and the same capacity, cover and largest loan,
  side by side with the period's. The Engine does not choose between them.
  Only with 12 months, so a year compares with a year.
- `tax_source` (`accountant` | `estimate`) is required with `tax` and echoed,
  so a report says whose figure it used; the Platform sends the accountant's
  when it has one. `report.bank` takes and passes both.

### 5a. Losses carried forward in `tax.estimate`

- The accountant named losses among what matters most. `tax.estimate` treated
  a loss year as nil and had no losses brought forward.
- `losses_forward` (individuals): s.382 losses of the farm trade, used after
  averaging and capital allowances against the profit charged to income tax,
  USC (s.531AU) and PRSI. The PRSI reading (SWCA s.2(1)) is not stated
  outright by Revenue / DSP, so the result labels it `reduced_unconfirmed`
  (decided with the user).
- Result `losses`: used, lost in a stock relief claim year (s.666(3)),
  this year's own loss, and what is carried forward.
- The young trained farmer / partnership caps measure the relief as tax saved
  against a year without it; that year re-applies the same losses (and the
  pension limit on its higher profit). Found in the branch review: without
  this, losses made an unrelieved year look taxable and clawed back tax on nil
  income.
- Not modelled: s.381 against other income (and the s.662 restriction),
  company losses (s.396), losses in `tax.partnership` and `plan.projection`.

### 5b. Pension contributions in `tax.estimate`

- The accountant named pensions paid among what matters. New
  `pension_contributions` with `birth_year` (needed: the age sets the %).
- Relief = the lower of the contributions and the age % (15–40%) of net
  relevant earnings capped at €115,000; it reduces income for **income tax
  only**. The rest is shown as `unrelieved` (carried forward by law).
- Net relevant earnings = the assessable farm profit after averaging,
  capital allowances and losses: under averaging this is the Engine's reading
  (decided with the user), labelled `earnings_basis`.
- Rules in `farm_functions/ie/pensions.py`. Not modelled: the spouse's own
  contributions, employer / company contributions, other relevant earnings.

### 5c. Home carer credit in `tax.estimate`

- The accountant named allowances "where only one spouse working". New
  `home_carer` (married; the Platform confirms the spouse cares for a
  dependant at home).
- Credit 1,800 (2024) / 1,950 (2025–26), less half the spouse's income above
  7,200. As Revenue does, it is given only when better than the second-earner
  band increase (`home_carer.applied`).
- 2027 limit not confirmed: claims for 2027 return `rule_not_available`
  (decided with the user); on the list to check when the Finance Act passes.
- Rules in `farm_functions/ie/home_carer.py`, separate from the yearly table.

### 5d. The spouse's own income in `tax.estimate`

- `tax.estimate` treated a spouse's income as PAYE pay only. Farm couples
  often have a spouse with their own trade, or paid wages by the farm.
- `spouse_self_employed_income`: earned income credit, own Class S PRSI,
  non-PAYE for the USC surcharge. `spouse_farm_wages` (sole traders): earned
  income credit, no employee credit (TDM 15-01-44), USC as PAYE pay, no PRSI
  (excepted employment, SWCA Sch. 1 Part 2). The employee and earned income
  credits share one cap per person. All of it counts for the second-earner
  band increase (s.15(4)) and as the carer's income for the home carer credit.
- `income` gains `spouse_self_employed_income` and `spouse_farm_wages` (0 when
  not sent) in every tax.estimate-shaped result.

### 6. `cf.reconcile`: from accounts profit to cash

- The accountant: accounts and cash differ most through merchant credit
  (40–50k outstanding is common), milk paid a month later and stock. A bank or
  accountant needs to see the monthly figures reconcile before trusting them.
- New ID `cf.reconcile` (same months for `pl.*` and `cf.*`): accounts
  operating profit (Operating Surplus + herd and stock value change, as
  `pl.net`), then the bridge — the non-cash value changes back out, the change
  in milk / co-op and other debtors, in merchant credit and other creditors —
  to the operating cash the months should show; `unexplained` in EUR and % of
  revenue. The Engine does not judge the difference (decided with the user).
- Merchant credit and milk debtors are their own inputs so the bridge names
  them. Operating cash only: capital spending, loans, drawings and tax are
  outside both sides (financing / investing in `cf.*`, not in the Operating
  Surplus).

### 7. `herd.valuation`: the herd on market value and Revenue practice

- The accountant: herd and stock are valued as numbers × average value, at
  60% of market value for Revenue or loans. Confirmed as Revenue practice
  (deemed cost: immature cattle 60%, sheep and pigs 75%; mature breeding stock
  at the value held since maturity, written down to market if lower).
- New ID `herd.valuation`: groups (category, head, market value per head, and
  for mature breeding stock the held value per head → `needs_input` without
  it) at a valuation date; returns both bases side by side; the Platform
  chooses which feeds accounts and tax (Revenue practice) and which a bank
  view (market). Market values are Platform data: the Engine has none.
- New rule status `practice` (Revenue practice, not statute) next to
  `enacted` / `announced`, so the source is never overstated.
- Rules in `farm_functions/ie/livestock_valuation.py`.

### 8a. Averaging step-out year in `tax.estimate`

- The accountant: step-out is seldom used, but it exists and farmers ask.
  `step_out` (averaging on) taxes the year on actual profit; the income tax
  saved against the averaged figure is deferred (never negative) and paid in
  4 equal instalments on 31 October from two years on (s.657(6A)).
- `last_step_out_year` (a year or "never") is needed to check the 4-year gap
  (`step_out_too_soon`). The instalment count and the gap are dated rules in
  `farm_functions/ie/averaging.py`.
- Not modelled: step-out in `tax.partnership` and `plan.projection` (decided
  with the user: rare).

### 8b. `tax.averaging_exit`: leaving averaging

- The accountant: "once in income averaging it's hard to get out of it" —
  because leaving tops up the 4 earlier years. New ID `tax.averaging_exit`:
  from the final averaged year's averaged profit and the 4 years assessed
  before it, the extra assessable profit per year (never lowering a year), the
  year the normal basis starts, and deferred step-out tax due at once
  (s.657(8)(d)–(e)); checked against Revenue's TDM Example 2.
- Profits only (decided with the user): the Engine's tax tables start in 2024
  and an exit reaches 4 years back, so the tax on each top-up is
  `tax.estimate` for that year where rules exist, else the accountant's.
- Exit inside `plan.projection` is not modelled (rare).

## Consequences
- Breaking for callers of `tax.estimate` that are individuals and of
  `tax.partnership`, and `plan.projection` tax profiles of individuals: they
  must send `income_averaging`; individual tax profiles also `preliminary_basis`
  and `tax_history`, and projected cash / net worth change with the new
  timing. `tax.capital_allowances` no longer takes `flat_rate_addition`.
  `debt.capacity` and the reports need `tax_source` with `tax`. 41 public IDs.
  Rule status gains `practice`. Engine 1.11.0.

## Related

ADR-0027, ADR-0036, ADR-0042, ADR-0053
