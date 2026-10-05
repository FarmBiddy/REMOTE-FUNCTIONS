"""Sector-agnostic seasonal run-rate projection (ADR-0026).

Periods are plain integer indexes and ``season`` is the cycle length (12 for
months); the caller maps calendars and decides which lines recur.
"""

from collections.abc import Iterable, Mapping

Lines = Mapping[str, float]


def run_rate(current: float, prior: float) -> float:
    """Growth factor current / prior; 1 when there is no prior to compare."""
    return current / prior if prior else 1.0


def run_rate_factors(
    history: Mapping[int, Lines], lines: Iterable[str], season: int
) -> dict[str, float]:
    """Factor per line over periods in the last season that have a prior-season match."""
    last = max(history)
    window = [p for p in history if p > last - season and p - season in history]
    return {
        line: run_rate(
            sum(history[p][line] for p in window),
            sum(history[p - season][line] for p in window),
        )
        for line in lines
    }


def latest_non_zero(history: Mapping[int, Lines], line: str) -> float:
    """Most recent non-zero value of ``line`` (e.g. last observed price), else 0."""
    for period in sorted(history, reverse=True):
        if history[period][line]:
            return history[period][line]
    return 0.0


def seasonal_projection(prior_season: float, factor: float) -> float:
    """Same period last season scaled by the run-rate factor."""
    return prior_season * factor


__all__ = ["latest_non_zero", "run_rate", "run_rate_factors", "seasonal_projection"]
