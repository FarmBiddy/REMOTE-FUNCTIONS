"""Revenue formulas. All amounts are annual EUR unless noted."""


def milk_revenue(milking_cows: float, litres_per_cow: float, milk_price: float) -> float:
    """Milk income = cows × litres per cow × price per litre."""
    return float(milking_cows) * float(litres_per_cow) * float(milk_price)


def scheme_revenue(
    biss: float = 0,
    acres: float = 0,
    other_grants: float = 0,
) -> float:
    """Subsidy / scheme income."""
    return float(biss) + float(acres) + float(other_grants)


def other_revenue(
    cattle_sales: float = 0,
    lamb_sales: float = 0,
    wool: float = 0,
    other: float = 0,
) -> float:
    """Non-milk, non-scheme income."""
    return float(cattle_sales) + float(lamb_sales) + float(wool) + float(other)


def total_revenue(
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
) -> float:
    """Milk + schemes + other revenue."""
    return (
        milk_revenue(milking_cows, litres_per_cow, milk_price)
        + scheme_revenue(biss, acres, other_grants)
        + other_revenue(cattle_sales, lamb_sales, wool, other)
    )
