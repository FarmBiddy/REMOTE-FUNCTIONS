"""Dairy KPIs over a set of months (ADR-0028).

Per-litre figures are in cents (c/L), the unit Irish dairy farmers, co-ops and
Teagasc use. Per-cow figures are in EUR. DSCR = Operating Surplus / loan
repayments (principal + interest).
"""

from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import round_money


def _cents_per_litre(amount: float, litres: float) -> float | None:
    value = per_unit(amount, litres)
    return None if value is None else round_money(value * 100)


def _per_cow(amount: float, cows: float) -> float | None:
    value = per_unit(amount, cows)
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
) -> dict:
    dscr = coverage_ratio(surplus, loan_repayments)
    return {
        "per_litre_c": {
            "revenue": _cents_per_litre(revenue, milk_litres),
            "costs": _cents_per_litre(costs, milk_litres),
            "surplus": _cents_per_litre(surplus, milk_litres),
            "cost_lines": {
                name: _cents_per_litre(amount, milk_litres) for name, amount in cost_lines.items()
            },
        },
        "per_cow": {
            "milk_litres": _per_cow(milk_litres, milking_cows),
            "revenue": _per_cow(revenue, milking_cows),
            "costs": _per_cow(costs, milking_cows),
            "surplus": _per_cow(surplus, milking_cows),
        },
        "dscr": None if dscr is None else round_money(dscr),
    }


__all__ = ["dairy_kpis"]
