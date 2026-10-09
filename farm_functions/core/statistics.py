"""Sector-agnostic averages (ADR-0052)."""

from collections.abc import Sequence
from math import exp, log


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float | None:
    """Σ value × weight / Σ weight; ``None`` when the weights sum to 0."""
    total = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total if total else None


def geometric_mean(values: Sequence[float]) -> float | None:
    """n-th root of the product (used for rolling hygiene averages); 0 if any value is 0."""
    if not values:
        return None
    if any(v == 0 for v in values):
        return 0.0
    return exp(sum(log(v) for v in values) / len(values))


__all__ = ["geometric_mean", "weighted_mean"]
