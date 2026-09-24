"""Dairy revenue formulas. All amounts are annual EUR unless noted.

``scheme_revenue`` remains Agriculture-owned; Dairy composes it in
``total_revenue`` and the Operating Statement.
"""

from farm_functions.agriculture.revenue import scheme_revenue
from farm_functions.core.aggregate import sum_amounts


def milk_revenue(milking_cows: float, litres_per_cow: float, milk_price: float) -> float:
    """Milk income = cows × litres per cow × price per litre."""
    return float(milking_cows) * float(litres_per_cow) * float(milk_price)


def other_revenue(
    cattle_sales: float = 0,
    land_leasing_income: float = 0,
    other: float = 0,
) -> float:
    """Non-milk, non-scheme Dairy operating income.

    ``land_leasing_income`` has Agriculture semantics (ADR-0013) but remains a
    Dairy contract field and is composed here once (no duplicate input).
    """
    return sum_amounts(cattle_sales, land_leasing_income, other)


def total_revenue(
    milking_cows: float,
    litres_per_cow: float,
    milk_price: float,
    biss: float = 0,
    acres: float = 0,
    other_grants: float = 0,
    cattle_sales: float = 0,
    land_leasing_income: float = 0,
    other: float = 0,
) -> float:
    """Milk + schemes + other revenue."""
    return sum_amounts(
        milk_revenue(milking_cows, litres_per_cow, milk_price),
        scheme_revenue(biss, acres, other_grants),
        other_revenue(cattle_sales, land_leasing_income, other),
    )


__all__ = [
    "milk_revenue",
    "other_revenue",
    "total_revenue",
]
