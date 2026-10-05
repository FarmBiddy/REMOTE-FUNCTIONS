"""Dairy KPIs over a set of months (ADR-0028, ADR-0032).

Per-litre figures are in cents (c/L), the unit Irish dairy farmers, co-ops and
Teagasc use. Per-cow, per-kg-milk-solids and per-hectare figures are in EUR.
DSCR = Operating Surplus / loan repayments (principal + interest).
"""

from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import round_money


def _cents_per_litre(amount: float, litres: float) -> float | None:
    value = per_unit(amount, litres)
    return None if value is None else round_money(value * 100)


def _per(amount: float, units: float) -> float | None:
    value = per_unit(amount, units)
    return None if value is None else round_money(value)


def dairy_kpis(
    *,
    milk_litres: float,
    milking_cows: float,
    revenue: float,
    costs: float,
    surplus: float,
    loan_repayments: float,
    cost_lines: dict[str, float],
    milk_solids_kg: float | None = None,
    hectares: float | None = None,
    debt_balance: float | None = None,
) -> dict:
    dscr = coverage_ratio(surplus, loan_repayments)

    def money_per(units: float) -> dict:
        amounts = {"revenue": revenue, "costs": costs, "surplus": surplus}
        return {name: _per(value, units) for name, value in amounts.items()}

    return {
        "per_litre_c": {
            "revenue": _cents_per_litre(revenue, milk_litres),
            "costs": _cents_per_litre(costs, milk_litres),
            "surplus": _cents_per_litre(surplus, milk_litres),
            "cost_lines": {
                name: _cents_per_litre(amount, milk_litres) for name, amount in cost_lines.items()
            },
        },
        "per_cow": {"milk_litres": _per(milk_litres, milking_cows), **money_per(milking_cows)},
        # Optional inputs: a block is null when its input was not sent. Debt is a
        # balance, so only stock-based ratios (per cow / ha), never per period litre.
        "per_kg_ms": None if milk_solids_kg is None else money_per(milk_solids_kg),
        "per_hectare": (
            None
            if hectares is None
            else {"milk_litres": _per(milk_litres, hectares), **money_per(hectares)}
        ),
        "debt": (
            None
            if debt_balance is None
            else {
                "balance": round_money(debt_balance),
                "per_cow": _per(debt_balance, milking_cows),
                "per_hectare": None if hectares is None else _per(debt_balance, hectares),
            }
        ),
        "dscr": None if dscr is None else round_money(dscr),
    }


__all__ = ["dairy_kpis"]
