"""Milk quality policy and component pricing (ADR-0052).

EU hygiene limits (Regulation (EC) 853/2004) are law, so they live here; herd
benchmarks and co-op price schedules are inputs and never stored.
"""

from typing import Literal, TypedDict


class QualityMetric(TypedDict):
    unit: str
    better: Literal["lower", "higher"]


QUALITY_METRICS: dict[str, QualityMetric] = {
    "scc_k": {"unit": "×1000 cells/ml", "better": "lower"},
    "tbc_k": {"unit": "×1000 cfu/ml", "better": "lower"},
    "fat_pct": {"unit": "%", "better": "higher"},
    "protein_pct": {"unit": "%", "better": "higher"},
}

# EU limits on rolling geometric means: (limit ×1000 per ml, window in months).
EU_LIMITS: dict[str, tuple[float, int]] = {"scc_k": (400.0, 3), "tbc_k": (100.0, 2)}

MILK_DENSITY_KG_PER_L = 1.03


def component_kg(milk_litres: float, pct: float) -> float:
    """kg of a component (fat or protein) in the milk."""
    return milk_litres * MILK_DENSITY_KG_PER_L * pct / 100


def milk_solids_kg(milk_litres: float, fat_pct: float, protein_pct: float) -> float:
    """kg milk solids = kg fat + kg protein."""
    return component_kg(milk_litres, fat_pct) + component_kg(milk_litres, protein_pct)


def band_adjustment_c(value_k: float, bands: list[dict]) -> float:
    """c/L adjustment of the first band whose ``max_k`` covers the value (last band open-ended)."""
    for band in bands:
        if band["max_k"] is None or value_k <= band["max_k"]:
            return band["adjustment_c"]
    return 0.0


__all__ = [
    "EU_LIMITS",
    "MILK_DENSITY_KG_PER_L",
    "QUALITY_METRICS",
    "band_adjustment_c",
    "component_kg",
    "milk_solids_kg",
]
