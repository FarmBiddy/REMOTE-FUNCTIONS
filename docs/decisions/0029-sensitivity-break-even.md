# Sensitivity scenarios and milk-price break-evens (`risk.sensitivity`)

## Status

Accepted (insights, step 1 of risk analysis; Monte Carlo deferred)

## Context

Farmers ask "what if the milk price drops 5c?" and "below what price am I in
trouble?". Answers must be exact and traceable before any probabilistic
analysis is added.

## Decision

1. **Input:** `pl_months` (actual + projected `pl.months` items), `cf_months`
   (consecutive `cf.months` items), `opening_cash`, and up to 20 `scenarios`.
   A "base" scenario (no shocks) is always returned first.
2. **Shocks per scenario:** `milk_price_c` (absolute, c/L, may be negative),
   `milk_volume_pct`, and `lines_pct` (% per line, ≥ −100) for any P&L or cash
   line except milk, which has its own shocks. Shared line IDs (ADR-0023) hit
   P&L and cash alike.
3. **Milk cheques scale with price × volume.** Cash `milk` is multiplied by
   `(1 + volume%) × (P + Δ) / P`, where P is the weighted average P&L milk price
   (Σ milk revenue / Σ litres). This keeps the cash line proportional to the
   P&L driver without modelling the payment lag again.
4. **Outcomes per scenario:** Operating Surplus, loan repayments, DSCR, closing
   cash, lowest month-end cash (period + amount), overdraft months. All come
   from the normal monthly statements and `cf.months` roll-forward.
5. **Break-evens (base only), solved exactly, not searched:** surplus and cash
   are linear in the price shift Δ.
   - Surplus: `S + L × Δ = 0` → `P − S / L`.
   - Cash: each month-end balance `C_k + (cumulative milk cash_k / P) × Δ ≥ 0`;
     the binding month gives the price. `null` when a month is negative before
     any milk cash (price cannot rescue it), or when there is no milk.
   Reported in c/L, floored at 0 (0 = covered even at a zero price). A cash
   break-even above the current price means the base already goes overdrawn.
6. Core holds the linear solving (`break_even_shift`,
   `min_shift_all_non_negative`); the Dairy milk vocabulary stays in the
   Application layer.

## Consequences

- Monte Carlo will reuse these shocks with sampled values (step 2).
- Not included: break-evens for drivers other than milk price, combined
  multi-driver break-even surfaces, KPI thresholds.

## Related

ADR-0023, ADR-0024, ADR-0026, ADR-0028
