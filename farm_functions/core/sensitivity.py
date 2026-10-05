"""Sector-agnostic linear break-even (ADR-0029).

An outcome that moves linearly with a driver shift ``d`` is
``value(d) = base + exposure × d``. These return the shift that brings it to 0.
"""

from collections.abc import Sequence


def break_even_shift(base: float, exposure: float) -> float | None:
    """Shift ``d`` where ``base + exposure × d = 0``; ``None`` if the driver has no effect."""
    return -base / exposure if exposure else None


def min_shift_all_non_negative(
    bases: Sequence[float], exposures: Sequence[float]
) -> float | None:
    """Smallest shift keeping every ``base + exposure × d ≥ 0`` (exposures ≥ 0).

    ``None`` when no shift can rescue a negative point (zero exposure there) or
    when the driver affects nothing.
    """
    shifts = []
    for base, exposure in zip(bases, exposures):
        if exposure:
            shifts.append(-base / exposure)
        elif base < 0:
            return None
    return max(shifts) if shifts else None


__all__ = ["break_even_shift", "min_shift_all_non_negative"]
