"""Milk quality, EU compliance, benchmarks and quality value (ADR-0052).

Application layer: weights statement figures by litres, applies the Dairy
quality policy (EU limits, density, component pricing, bands) and compares with
benchmarks the Platform supplies.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.ratios import per_unit
from farm_functions.core.rounding import round_margin_pct, round_money
from farm_functions.core.statistics import geometric_mean, weighted_mean
from farm_functions.dairy.quality import (
    AVERAGE_TOLERANCE,
    EU_LIMITS,
    QUALITY_METRICS,
    band_adjustment_c,
    component_kg,
    milk_solids_kg,
)

_METRICS = tuple(QUALITY_METRICS)


def _index(m: dict[str, Any]) -> int:
    return m["year"] * 12 + m["month"] - 1


def _period(m: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "month", "year": m["year"], "month": m["month"]}


def _round(value: float | None) -> float | None:
    return None if value is None else round_money(value)


def _rolling(months: list[dict[str, Any]], metric: str) -> list[float]:
    """Geometric mean over the calendar window ending at each month (months available)."""
    _, window = EU_LIMITS[metric]
    by_index = {_index(m): m[metric] for m in months}
    return [
        geometric_mean([by_index[i] for i in range(_index(m) - window + 1, _index(m) + 1) if i in by_index])
        for m in months
    ]


def _benchmarks(period: dict[str, float], benchmarks: dict[str, Any] | None) -> dict[str, Any] | None:
    if not benchmarks:
        return None
    out = {}
    for metric in _METRICS:
        ref = benchmarks.get(metric)
        if not ref:
            continue
        farm = period[metric]
        lower_is_better = QUALITY_METRICS[metric]["better"] == "lower"

        def better(reference: float | None) -> bool | None:
            if reference is None:
                return None
            return farm <= reference if lower_is_better else farm >= reference

        def gap(reference: float | None) -> float | None:
            return None if reference is None else round_money(farm - reference)

        average = ref["average"]
        to_average = gap(average)
        if to_average is None:
            position = None
        elif abs(to_average) <= AVERAGE_TOLERANCE[metric]:
            position = "about"
        else:
            position = "above" if to_average > 0 else "below"
        out[metric] = {
            "farm": farm,
            "average": average,
            "gap_to_average": to_average,
            # "above" / "below" are numeric; better_than_average says which is good.
            "position": position,
            "better_than_average": None if position in (None, "about") else better(average),
            "best20": ref["best20"],
            "gap_to_best20": gap(ref["best20"]),
            "better_than_best20": better(ref["best20"]),
            "top10": ref["top10"],
            "gap_to_top10": gap(ref["top10"]),
            "better_than_top10": better(ref["top10"]),
        }
    return out


def _value(months: list[dict[str, Any]], pricing: dict[str, Any], period: dict[str, float],
           benchmarks: dict[str, Any] | None, litres: float) -> dict[str, Any]:
    eur = {"fat": 0.0, "protein": 0.0, "volume_charge": 0.0, "scc_adjustment": 0.0, "tbc_adjustment": 0.0}
    best_band_gain = 0.0
    for m in months:
        eur["fat"] += component_kg(m["milk_litres"], m["fat_pct"]) * pricing["fat_eur_per_kg"]
        eur["protein"] += component_kg(m["milk_litres"], m["protein_pct"]) * pricing["protein_eur_per_kg"]
        eur["volume_charge"] -= m["milk_litres"] * pricing["volume_charge_c_per_l"] / 100
        for metric, bands_key in (("scc_k", "scc_bands"), ("tbc_k", "tbc_bands")):
            bands = pricing[bands_key]
            if not bands:
                continue
            actual = band_adjustment_c(m[metric], bands)
            eur[f"{metric[:3]}_adjustment"] += m["milk_litres"] * actual / 100
            best_band_gain += m["milk_litres"] * (max(b["adjustment_c"] for b in bands) - actual) / 100
    total = sum_amounts(*eur.values())

    def gain_to(level: str) -> float | None:
        """Extra fat / protein value if the farm matched ``level`` composition (0 if at or above)."""
        gain = None
        for metric, price_key in (("fat_pct", "fat_eur_per_kg"), ("protein_pct", "protein_eur_per_kg")):
            target = ((benchmarks or {}).get(metric) or {}).get(level)
            if target is not None and period[metric] is not None:
                # Linear in %: Σ months (target − pct_m) × litres_m = (target − weighted pct) × litres.
                shortfall = max(0.0, target - period[metric])
                gain = (gain or 0.0) + component_kg(litres, shortfall) * pricing[price_key]
        return _round(gain)

    def c_per_litre(amount: float) -> float | None:
        value = per_unit(amount, litres)
        return None if value is None else round_money(value * 100)

    return {
        **{f"{k}_eur": round_money(v) for k, v in eur.items()},
        "total_eur": round_money(total),
        "price_c_per_l": {**{k: c_per_litre(v) for k, v in eur.items()}, "total": c_per_litre(total)},
        "gain_to_average_eur": gain_to("average"),
        "gain_to_best20_eur": gain_to("best20"),
        "gain_to_top10_eur": gain_to("top10"),
        "gain_at_best_band_eur": round_money(best_band_gain),
    }


def milk_quality(
    *,
    months: list[dict[str, Any]],
    milking_cows: float | None = None,
    hectares: float | None = None,
    benchmarks: dict[str, Any] | None = None,
    pricing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``milk.quality``: weighted quality figures, EU compliance, benchmarks and value."""
    months = sorted(months, key=_index)
    litres = sum_amounts(*(m["milk_litres"] for m in months))
    weights = [m["milk_litres"] for m in months]
    raw = {metric: weighted_mean([m[metric] for m in months], weights) for metric in _METRICS}
    period_values = {
        "fat_pct": raw["fat_pct"], "protein_pct": raw["protein_pct"], "scc_k": raw["scc_k"], "tbc_k": raw["tbc_k"],
    }
    rounded = {
        k: None if v is None else (round_margin_pct(v) if k.endswith("_pct") else round_money(v))
        for k, v in period_values.items()
    }
    solids = sum_amounts(*(milk_solids_kg(m["milk_litres"], m["fat_pct"], m["protein_pct"]) for m in months))

    rolling = {metric: _rolling(months, metric) for metric in EU_LIMITS}
    month_rows, breaches = [], {metric: [] for metric in EU_LIMITS}
    for i, m in enumerate(months):
        row = {
            "period": _period(m),
            "milk_litres": round_money(m["milk_litres"]),
            **{metric: m[metric] for metric in _METRICS},
            "milk_solids_kg": round_money(milk_solids_kg(m["milk_litres"], m["fat_pct"], m["protein_pct"])),
        }
        for metric, (limit, _) in EU_LIMITS.items():
            value = rolling[metric][i]
            row[f"{metric[:3]}_rolling_k"] = round_money(value)
            row[f"{metric[:3]}_breach"] = value > limit
            if value > limit:
                breaches[metric].append(_period(m))
        month_rows.append(row)

    comparable = {k: v for k, v in rounded.items() if v is not None}
    return {
        "from": _period(months[0]),
        "to": _period(months[-1]),
        "month_count": len(months),
        "period": {
            "milk_litres": round_money(litres),
            **rounded,
            "milk_solids_kg": round_money(solids),
            "kg_ms_per_cow": None if milking_cows is None else _round(per_unit(solids, milking_cows)),
            "kg_ms_per_ha": None if hectares is None else _round(per_unit(solids, hectares)),
        },
        "months": month_rows,
        "compliance": {
            "scc_limit_k": EU_LIMITS["scc_k"][0],
            "tbc_limit_k": EU_LIMITS["tbc_k"][0],
            "scc_breach_months": breaches["scc_k"],
            "tbc_breach_months": breaches["tbc_k"],
        },
        "vs_benchmarks": _benchmarks(comparable, benchmarks) if litres else None,
        "value": None if pricing is None else {"currency": "EUR", **_value(months, pricing, period_values, benchmarks, litres)},
    }
