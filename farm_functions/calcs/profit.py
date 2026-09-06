"""Profit formulas. Revenue and costs are already-totalled annual EUR."""


def net_profit(revenue: float, costs: float) -> float:
    """Profit = revenue − costs."""
    return float(revenue) - float(costs)


def profit_margin(revenue: float, costs: float) -> float:
    """Profit as a 0–1 ratio of revenue. Returns 0 when revenue is 0 or negative."""
    revenue = float(revenue)
    if revenue <= 0:
        return 0.0
    return net_profit(revenue, costs) / revenue


def profit_margin_pct(revenue: float, costs: float) -> float:
    """Profit margin as a percentage of revenue."""
    return profit_margin(revenue, costs) * 100
