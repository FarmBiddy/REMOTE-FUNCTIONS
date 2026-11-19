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
- Rules (90 / 100 / 105%) and ROS dates live in `farm_functions/ie/preliminary.py`.


- Breaking for callers of `tax.estimate` that are individuals and of
  `tax.partnership`, and `plan.projection` tax profiles of individuals: they
  must send `income_averaging`. Engine 1.11.0.

## Related

ADR-0027, ADR-0036, ADR-0042, ADR-0053
