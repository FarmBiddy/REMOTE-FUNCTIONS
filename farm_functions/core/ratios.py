"""Sector-agnostic per-unit and coverage ratios (ADR-0028).

Return ``None`` when the divisor is 0: a ratio with nothing to divide by is
undefined, not zero.
"""


def per_unit(amount: float, units: float) -> float | None:
    """Amount per unit (e.g. EUR per litre, EUR per head)."""
    return amount / units if units else None


def coverage_ratio(available: float, obligation: float) -> float | None:
    """Times an obligation is covered (e.g. debt service cover ratio)."""
    return available / obligation if obligation else None


__all__ = ["coverage_ratio", "per_unit"]
