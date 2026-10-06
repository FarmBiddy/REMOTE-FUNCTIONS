"""Sector-agnostic compound growth (ADR-0042)."""

from collections.abc import Sequence


def compound_indexes(rates_pct: Sequence[float], periods: int) -> list[float]:
    """Cumulative index per period from % changes; missing periods change by 0%.

    ``[10, 0, 5]`` over 4 periods → ``[1.1, 1.1, 1.155, 1.155]``.
    """
    index, out = 1.0, []
    for period in range(periods):
        rate = rates_pct[period] if period < len(rates_pct) else 0.0
        index *= 1 + rate / 100
        out.append(index)
    return out


def carry_forward(values: Sequence[float], periods: int, default: float) -> list[float]:
    """Value per period: given values, then the last one repeated; ``default`` if none."""
    out, last = [], default
    for period in range(periods):
        if period < len(values):
            last = values[period]
        out.append(last)
    return out


__all__ = ["carry_forward", "compound_indexes"]
