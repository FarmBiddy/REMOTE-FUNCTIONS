# Partial budget (`decision.partial_budget`)

## Status

Accepted (analysis)

## Context

Most farm decisions change part of the business: rent more land, contract-rear
heifers, buy feed instead of making silage, add cows. The standard tool
(Teagasc and farm-management textbooks) is the partial budget: only what
changes is counted. It applies to any enterprise, so it is the first
enterprise-independent decision tool.

## Decision

1. Input: four lists of labelled **annual** amounts (≤ 30 each):
   `added_income`, `reduced_costs` (gains) and `added_costs`, `reduced_income`
   (losses). Labels are free text (1–60 chars) owned by the Platform. Optional
   `capital {amount, life_years, annual_rate}`.
2. **Capital charge** = straight-line depreciation (`amount / life_years`) +
   interest on the average capital tied up (`amount / 2 × annual_rate`).
3. Output: each list with its total; `gains`; `losses` (including the capital
   charge); `operating_change` (gains − operating losses); `net_change`;
   `worthwhile` (net > 0). With capital: `simple_payback_years` = amount /
   operating change (`null` when not positive) and
   `return_on_investment_pct` = (operating change − depreciation) / amount.
4. Steady-state, one typical year. Timing and multi-year effects go to
   `plan.projection` (ADR-0042); discounted returns to the investment appraisal
   ID (next ADR).
5. Core holds the capital-charge formula; the tool lives in an
   enterprise-independent Application module (`decisions.py`).

## Consequences

- `worthwhile` is arithmetic, not advice: risk, labour and lifestyle remain
  the farmer's call (Biddy / advisor present it).

## Related

ADR-0031, ADR-0042
