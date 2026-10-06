# Investment appraisal: NPV, IRR, discounted payback (`decision.investment`)

## Status

Accepted (analysis)

## Context

`risk.sensitivity` answers "can I afford it?" (cash, DSCR) and
`decision.partial_budget` "is a typical year better?". Long-lived investments
(a parlour lasts 15–20 years) also need "is it a good use of capital over its
life?", the standard capital-budgeting view banks and advisors use.

## Decision

1. Input: `amount` (year-0 outlay), `discount_rate` (0–1, **required**: it is
   the user's or lender's cost of capital, not an Engine opinion), benefits as
   **either** constant `annual_benefit` + `life_years` (1–40) **or** explicit
   `cash_flows` (year 1 first, may be negative, ≤ 40), and optional
   `residual_value` added to the last year. Anything else →
   `details.reason: benefit_form`.
2. Core (enterprise-independent):
   - **NPV** = Σ cash flow / (1 + rate)^year, year 0 = −amount.
   - **IRR** = the rate where NPV = 0, by bisection in (−99%, 1000%); `null`
     when NPV never changes sign. May be negative.
   - **Discounted payback** = years until the cumulative discounted cash flow
     reaches 0, interpolated within the year; `null` if never. Simple payback is
     the same at a 0% rate.
3. Output: `npv`, `irr_pct`, `simple_payback_years`,
   `discounted_payback_years`, `profitability_index` (PV of benefits / amount;
   `null` when the amount is 0), `worthwhile` (NPV > 0) and the year-by-year
   schedule (cash flow, discount factor, present value, cumulative PV).
4. Pre-tax, nominal cash flows; inflation and tax relief are the caller's
   choice of inputs and rate.

## Consequences

- Pair with `risk.sensitivity` investments (affordability) and
  `decision.partial_budget` (typical-year effect) for a full decision.
- Not included: tax allowances, financing structure inside the NPV (the
  discount rate carries the cost of capital), real-option analysis.

## Related

ADR-0031, ADR-0036, ADR-0045
