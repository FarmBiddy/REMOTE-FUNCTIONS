"""Sector-agnostic investment and decision maths (ADR-0045, ADR-0046)."""

from collections.abc import Sequence


def annual_capital_charge(amount: float, life_years: float, annual_rate: float) -> tuple[float, float]:
    """(depreciation, interest) per year: straight-line over the life plus
    interest on the average capital tied up (half the investment)."""
    return amount / life_years, amount / 2 * annual_rate


def npv(rate: float, flows: Sequence[float]) -> float:
    """Net present value; ``flows[0]`` is year 0 (usually the negative outlay)."""
    return sum(flow / (1 + rate) ** year for year, flow in enumerate(flows))


def irr(flows: Sequence[float], low: float = -0.99, high: float = 10.0) -> float | None:
    """Internal rate of return by bisection: the rate where NPV = 0.

    ``None`` when NPV has no sign change in [low, high] (e.g. never pays back).
    """
    f_low, f_high = npv(low, flows), npv(high, flows)
    if f_low == 0:
        return low
    if f_low * f_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv(mid, flows)
        if abs(f_mid) < 1e-9 or high - low < 1e-12:
            return mid
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


def discounted_payback(rate: float, flows: Sequence[float]) -> float | None:
    """Years until cumulative discounted cash flow turns ≥ 0, interpolated within
    the year; ``None`` if it never does."""
    cumulative = 0.0
    for year, flow in enumerate(flows):
        present = flow / (1 + rate) ** year
        if cumulative < 0 <= cumulative + present:
            return year - 1 + (-cumulative / present)
        cumulative += present
    return 0.0 if flows and flows[0] >= 0 else None


__all__ = ["annual_capital_charge", "discounted_payback", "irr", "npv"]
