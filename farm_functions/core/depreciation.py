"""Sector-agnostic depreciation (ADR-0037).

``months_held`` counts depreciated months, the acquisition month included.
Calendar-blind: the caller maps dates to month counts.
"""


def straight_line_nbv(cost: float, residual: float, life_months: int, months_held: int) -> float:
    """Net book value after ``months_held``: equal monthly charges down to ``residual``."""
    if months_held <= 0:
        return cost
    monthly = (cost - residual) / life_months
    return max(residual, cost - monthly * months_held)


def reducing_balance_nbv(cost: float, annual_rate: float, months_held: int) -> float:
    """Net book value after ``months_held`` at ``annual_rate`` of the remaining value a year."""
    if months_held <= 0:
        return cost
    return cost * (1 - annual_rate) ** (months_held / 12)


__all__ = ["reducing_balance_nbv", "straight_line_nbv"]
