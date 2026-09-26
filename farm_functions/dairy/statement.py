"""Canonical Phase 1 Dairy annual Operating Statement composition.

Composes Dairy milk/other income, Agriculture schemes, and Core surplus /
rounding. Does not reimplement those primitives.
"""

from farm_functions.agriculture.revenue import scheme_revenue
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES, total_costs
from farm_functions.dairy.revenue import milk_revenue, other_revenue


def pl_summary(
    milking_cows: float,
    litres_per_cow: float,
    milk_price: float,
    biss: float = 0,
    acres: float = 0,
    other_grants: float = 0,
    cattle_sales: float = 0,
    land_leasing_income: float = 0,
    other: float = 0,
    feed: float = 0,
    fertiliser: float = 0,
    vet: float = 0,
    contractor: float = 0,
    labour: float = 0,
    insurance: float = 0,
    fuel: float = 0,
    electricity: float = 0,
    water: float = 0,
    repairs_maintenance: float = 0,
    rent_lease: float = 0,
    professional_fees: float = 0,
    levies: float = 0,
    other_operating_costs: float = 0,
    loan_repayments: float = 0,
) -> dict:
    """Annual dairy P&L with Operating Surplus and separate finance reporting."""
    milk = milk_revenue(milking_cows, litres_per_cow, milk_price)
    schemes = scheme_revenue(biss, acres, other_grants)
    other_income = other_revenue(cattle_sales, land_leasing_income, other)
    revenue = sum_amounts(milk, schemes, other_income)
    cost_lines = {
        "feed": float(feed),
        "fertiliser": float(fertiliser),
        "vet": float(vet),
        "contractor": float(contractor),
        "labour": float(labour),
        "insurance": float(insurance),
        "fuel": float(fuel),
        "electricity": float(electricity),
        "water": float(water),
        "repairs_maintenance": float(repairs_maintenance),
        "rent_lease": float(rent_lease),
        "professional_fees": float(professional_fees),
        "levies": float(levies),
        "other_operating_costs": float(other_operating_costs),
    }
    costs = total_costs(**{name: cost_lines[name] for name in OPERATING_COST_CATEGORIES})
    profit = net_profit(revenue, costs)
    return {
        "currency": "EUR",
        "period": "annual",
        "revenue": {
            "milk": round_money(milk),
            "schemes": round_money(schemes),
            "other": round_money(other_income),
            "total": round_money(revenue),
        },
        "costs": {
            "lines": {name: round_money(cost_lines[name]) for name in OPERATING_COST_CATEGORIES},
            "total": round_money(costs),
        },
        "profit": {
            "net": round_money(profit),
            "margin": round_margin_ratio(profit_margin(revenue, costs)),
            "margin_pct": round_margin_pct(profit_margin_pct(revenue, costs)),
        },
        "finance": {
            "loan_repayments": round_money(float(loan_repayments)),
        },
    }


__all__ = ["pl_summary"]
