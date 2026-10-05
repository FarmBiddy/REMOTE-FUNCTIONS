"""Sector-agnostic variance analysis (ADR-0035)."""


def change_pct(actual: float, comparison: float) -> float | None:
    """Percentage change against the comparison; ``None`` when it is 0."""
    return (actual - comparison) / abs(comparison) * 100 if comparison else None


def price_volume_effects(
    actual_qty: float, actual_price: float, comparison_qty: float, comparison_price: float
) -> tuple[float, float]:
    """Split a revenue change into (volume effect, price effect).

    Volume at the comparison price, price on the actual volume, so the two
    effects add up exactly to actual revenue − comparison revenue.
    """
    volume = (actual_qty - comparison_qty) * comparison_price
    price = (actual_price - comparison_price) * actual_qty
    return volume, price


__all__ = ["change_pct", "price_volume_effects"]
