"""Operating Surplus formulas. Revenue and costs are already-totalled annual EUR.

Phase 1: ``net_profit`` computes Operating Surplus = operating income − operating
costs. Public calculation ID ``profit.net`` is unchanged.
"""


def net_profit(revenue: float, costs: float) -> float:
    """Operating Surplus = revenue − operating costs."""
    return float(revenue) - float(costs)


def profit_margin(revenue: float, costs: float) -> float:
    """Operating Surplus as a 0–1 ratio of revenue. Returns 0 when revenue is 0 or negative."""
    revenue = float(revenue)
    if revenue <= 0:
        return 0.0
    return net_profit(revenue, costs) / revenue


def profit_margin_pct(revenue: float, costs: float) -> float:
    """Operating Surplus margin as a percentage of revenue."""
    return profit_margin(revenue, costs) * 100
