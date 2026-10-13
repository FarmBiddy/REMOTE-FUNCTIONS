"""Irish income tax, USC, PRSI and corporation tax by tax year (ADR-0053).

Values: ``docs/ie-rules.md`` §2–3. Each value is a dated rule; a tax year with
any value missing has no estimate (no extrapolation). 2027 figures are Budget
2027 announcements until Finance Act 2026.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

_YEARS = (2024, 2025, 2026, 2027)
LAST_TAX_YEAR = _YEARS[-1]


def _yearly(rule_id: str, values: tuple[float, ...], legal_ref: str, announced_from: int | None = None) -> tuple[Rule, ...]:
    return tuple(
        Rule(
            rule_id, v, date(y, 1, 1), date(y, 12, 31),
            "Budget 2027" if announced_from and y >= announced_from else legal_ref,
            "announced" if announced_from and y >= announced_from else "enacted",
        )
        for y, v in zip(_YEARS, values)
    )


def _fixed(rule_id: str, value: float, legal_ref: str) -> tuple[Rule, ...]:
    return (Rule(rule_id, value, date(_YEARS[0], 1, 1), date(_YEARS[-1], 12, 31), legal_ref, "enacted"),)


RULES: dict[str, tuple[Rule, ...]] = {
    # Income tax (TCA s.15, s.461, s.472, s.472AB)
    "it_rate_standard": _fixed("it_rate_standard", 20.0, "TCA s.15"),
    "it_rate_higher": _fixed("it_rate_higher", 40.0, "TCA s.15"),
    "it_band_single": _yearly("it_band_single", (42_000, 44_000, 44_000, 46_500), "TCA s.15", 2027),
    "it_band_married_one_income": _yearly(
        "it_band_married_one_income", (51_000, 53_000, 53_000, 55_500), "TCA s.15", 2027
    ),
    "it_band_married_second_income_max": _yearly(
        "it_band_married_second_income_max", (33_000, 35_000, 35_000, 37_500), "TCA s.15", 2027
    ),
    "it_credit_personal_single": _yearly(
        "it_credit_personal_single", (1_875, 2_000, 2_000, 2_125), "TCA s.461", 2027
    ),
    "it_credit_personal_married": _yearly(
        "it_credit_personal_married", (3_750, 4_000, 4_000, 4_250), "TCA s.461", 2027
    ),
    "it_credit_earned_income": _yearly("it_credit_earned_income", (1_875, 2_000, 2_000, 2_125), "TCA s.472AB", 2027),
    "it_credit_employee": _yearly("it_credit_employee", (1_875, 2_000, 2_000, 2_125), "TCA s.472", 2027),
    # USC (TCA s.531AN): 0.5% to 12,012; 2% to the yearly ceiling; middle rate to 70,044; 8% above.
    "usc_exemption_threshold": _fixed("usc_exemption_threshold", 13_000, "TCA Part 18D"),
    "usc_band_low_ceiling": _fixed("usc_band_low_ceiling", 12_012, "TCA s.531AN"),
    "usc_band_2pct_ceiling": _yearly("usc_band_2pct_ceiling", (25_760, 27_382, 28_700, 30_300), "TCA s.531AN", 2027),
    "usc_rate_middle": _yearly("usc_rate_middle", (4.0, 3.0, 3.0, 3.0), "TCA s.531AN"),
    "usc_band_middle_ceiling": _fixed("usc_band_middle_ceiling", 70_044, "TCA s.531AN"),
    "usc_surcharge_threshold": _fixed("usc_surcharge_threshold", 100_000, "TCA s.531AN"),
    # PRSI (SWCA s.13 as amended by SW(MP)A 2024): rate changes each October, so
    # the tax-year rate is 9 months old + 3 months new (2027 is our arithmetic).
    "prsi_s_rate": _yearly("prsi_s_rate", (4.025, 4.125, 4.2375, 4.3875), "SWCA s.13"),
    "prsi_s_minimum": _yearly("prsi_s_minimum", (537.5, 650, 650, 650), "SWCA s.13"),
    "prsi_s_threshold": _fixed("prsi_s_threshold", 5_000, "SWCA s.13"),
    "prsi_a_rate": _yearly("prsi_a_rate", (4.025, 4.125, 4.2375, 4.3875), "SWCA s.13"),
    "prsi_a_weekly_exemption": _fixed("prsi_a_weekly_exemption", 352, "SWCA s.13"),
    # Corporation tax (TCA s.21, s.21A)
    "ct_rate_trading": _fixed("ct_rate_trading", 12.5, "TCA s.21"),
    "ct_rate_non_trading": _fixed("ct_rate_non_trading", 25.0, "TCA s.21A"),
    # Stock relief caps on tax value (IT + USC saved)
    "stock_relief_ytf_cap": _fixed("stock_relief_ytf_cap", 40_000, "TCA s.667B(5A)"),
    "state_aid_young_farmer_lifetime": _fixed(
        "state_aid_young_farmer_lifetime", 100_000, "Reg. (EU) 2022/2472 art. 18(7); TCA s.667B(7)"
    ),
    "stock_relief_rfp_de_minimis": _fixed("stock_relief_rfp_de_minimis", 20_000, "TCA s.667C(3A)"),
}


def year_rules(tax_year: int) -> dict[str, Rule] | None:
    """Every rule in force for the tax year, or None if any is missing."""
    found = {k: rule_at(v, date(tax_year, 1, 1)) for k, v in RULES.items()}
    return None if any(r is None for r in found.values()) else found


def banded(income: float, ceilings: tuple[float, ...], rates_pct: tuple[float, ...]) -> float:
    """Tax on ``income`` with ``rates_pct[i]`` up to ``ceilings[i]`` and the last rate above."""
    tax, floor = 0.0, 0.0
    for ceiling, rate in zip((*ceilings, float("inf")), rates_pct):
        tax += max(min(income, ceiling) - floor, 0.0) * rate / 100
        floor = ceiling
    return tax


__all__ = ["LAST_TAX_YEAR", "RULES", "banded", "year_rules"]
