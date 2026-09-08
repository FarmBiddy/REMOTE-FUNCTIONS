"""Composite P&L: calls the atomic formulas and returns one payload."""

from farm_functions.calcs.costs import COST_CATEGORIES, total_costs
from farm_functions.calcs.profit import net_profit, profit_margin, profit_margin_pct
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.rounding import round_margin_pct, round_margin_ratio, round_money


def pl_summary(
    milking_cows: float,
    litres_per_cow: float,
    milk_price: float,
    biss: float = 0,
    acres: float = 0,
    other_grants: float = 0,
    cattle_sales: float = 0,
    lamb_sales: float = 0,
    wool: float = 0,
    other: float = 0,
    feed: float = 0,
    fertiliser: float = 0,
    vet: float = 0,
    contractor: float = 0,
    labour: float = 0,
    insurance: float = 0,
    loan_repayments: float = 0,
    fuel: float = 0,
    electricity: float = 0,
) -> dict:
    milk = milk_revenue(milking_cows, litres_per_cow, milk_price)
    schemes = scheme_revenue(biss, acres, other_grants)
    other_income = other_revenue(cattle_sales, lamb_sales, wool, other)
    revenue = total_revenue(
        milking_cows,
        litres_per_cow,
        milk_price,
        biss=biss,
        acres=acres,
        other_grants=other_grants,
        cattle_sales=cattle_sales,
        lamb_sales=lamb_sales,
        wool=wool,
        other=other,
    )
    cost_lines = {
        "feed": float(feed),
        "fertiliser": float(fertiliser),
        "vet": float(vet),
        "contractor": float(contractor),
        "labour": float(labour),
        "insurance": float(insurance),
        "loan_repayments": float(loan_repayments),
        "fuel": float(fuel),
        "electricity": float(electricity),
    }
    costs = total_costs(**{name: cost_lines[name] for name in COST_CATEGORIES})
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
            "lines": {name: round_money(cost_lines[name]) for name in COST_CATEGORIES},
            "total": round_money(costs),
        },
        "profit": {
            "net": round_money(profit),
            "margin": round_margin_ratio(profit_margin(revenue, costs)),
            "margin_pct": round_margin_pct(profit_margin_pct(revenue, costs)),
        },
    }
