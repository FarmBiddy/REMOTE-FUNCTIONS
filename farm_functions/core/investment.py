"""Sector-agnostic investment and decision maths (ADR-0045)."""


def annual_capital_charge(amount: float, life_years: float, annual_rate: float) -> tuple[float, float]:
    """(depreciation, interest) per year: straight-line over the life plus
    interest on the average capital tied up (half the investment)."""
    return amount / life_years, amount / 2 * annual_rate


__all__ = ["annual_capital_charge"]
