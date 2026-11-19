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

## Consequences

- Breaking for callers of `tax.estimate` that are individuals and of
  `tax.partnership`: they must send `income_averaging`. Engine 1.11.0.

## Related

ADR-0027, ADR-0036, ADR-0042, ADR-0053
