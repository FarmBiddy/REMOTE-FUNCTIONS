"""Irish flat-rate farmer VAT addition (s.86 VATCA 2010; ADR-0053).

Unregistered (flat-rate) farmers receive the addition on top of the price of
agricultural produce sold to VAT-registered buyers (milk to the co-op, cattle
to a factory or through a mart), computed on the gross price before contra
deductions. Rates: ``docs/ie-rules.md`` §1.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule

_ID = "vat_fra"

FLAT_RATE_ADDITION: tuple[Rule, ...] = (
    Rule(_ID, 5.4, date(2015, 1, 1), date(2020, 12, 31), "s.86 VATCA 2010 (FA2014 s.67)", "enacted"),
    Rule(_ID, 5.6, date(2021, 1, 1), date(2021, 12, 31), "FA2020 s.40", "enacted"),
    Rule(_ID, 5.5, date(2022, 1, 1), date(2022, 12, 31), "FA2021 s.54", "enacted"),
    Rule(_ID, 5.0, date(2023, 1, 1), date(2023, 12, 31), "FA2022 s.56", "enacted"),
    Rule(_ID, 4.8, date(2024, 1, 1), date(2024, 12, 31), "F(No.2)A2023 s.62", "enacted"),
    Rule(_ID, 5.1, date(2025, 1, 1), date(2025, 12, 31), "FA2024 s.83", "enacted"),
    Rule(_ID, 4.5, date(2026, 1, 1), date(2026, 12, 31), "FA2025 s.73", "enacted"),
    Rule(_ID, 4.8, date(2027, 1, 1), None, "Budget 2027 §4.9", "announced"),
)


def flat_rate_addition(agricultural_sales: float, rate_pct: float) -> float:
    """Addition = sales (ex-VAT, gross of contra deductions) × rate %."""
    return float(agricultural_sales) * float(rate_pct) / 100


__all__ = ["FLAT_RATE_ADDITION", "flat_rate_addition"]
