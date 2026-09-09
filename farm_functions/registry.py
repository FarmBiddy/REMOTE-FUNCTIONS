"""Authoritative catalogue of public calculation IDs for agents and HTTP clients.

Public IDs (e.g. ``revenue.milk``) are stable contract identifiers. They are set
explicitly on each ``CalculationDefinition`` and are independent of Python
handler, module, or class names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from farm_functions.calcs.costs import total_costs
from farm_functions.calcs.profit import net_profit, profit_margin, profit_margin_pct
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.calcs.summary import pl_summary
from farm_functions.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.schemas import (
    MilkRevenueInput,
    OtherRevenueInput,
    PlSummaryInput,
    ProfitInput,
    SchemeRevenueInput,
    TotalCostsInput,
    TotalRevenueInput,
)


@dataclass(frozen=True)
class CalculationDefinition:
    """One registered calculation. ``id`` is the stable public calculation ID."""

    id: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]
    supports_provenance: bool

    @property
    def required(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, field in self.input_model.model_fields.items()
            if field.is_required()
        )

    @property
    def optional(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, field in self.input_model.model_fields.items()
            if not field.is_required()
        )


def _money(value: float) -> dict[str, float]:
    return {"amount": round_money(value), "currency": "EUR"}


def _handle_milk_revenue(**kwargs: Any) -> dict[str, Any]:
    return _money(milk_revenue(**kwargs))


def _handle_scheme_revenue(**kwargs: Any) -> dict[str, Any]:
    return _money(scheme_revenue(**kwargs))


def _handle_other_revenue(**kwargs: Any) -> dict[str, Any]:
    return _money(other_revenue(**kwargs))


def _handle_total_revenue(**kwargs: Any) -> dict[str, Any]:
    return _money(total_revenue(**kwargs))


def _handle_total_costs(**kwargs: Any) -> dict[str, Any]:
    return _money(total_costs(**kwargs))


def _handle_net_profit(**kwargs: Any) -> dict[str, Any]:
    return _money(net_profit(**kwargs))


def _handle_profit_margin(**kwargs: Any) -> dict[str, Any]:
    revenue = kwargs["revenue"]
    costs = kwargs["costs"]
    return {
        "margin": round_margin_ratio(profit_margin(revenue, costs)),
        "margin_pct": round_margin_pct(profit_margin_pct(revenue, costs)),
        "profit": round_money(net_profit(revenue, costs)),
        "revenue": round_money(revenue),
        "costs": round_money(costs),
        "currency": "EUR",
    }


# Authoritative ordered catalogue. Public IDs are the ``id`` fields only.
CALCULATION_CATALOGUE: tuple[CalculationDefinition, ...] = (
    CalculationDefinition(
        id="revenue.milk",
        description="Annual milk revenue: cows × litres per cow × price per litre.",
        input_model=MilkRevenueInput,
        handler=_handle_milk_revenue,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="revenue.schemes",
        description="Annual scheme / subsidy income (BISS, ACRES, other grants).",
        input_model=SchemeRevenueInput,
        handler=_handle_scheme_revenue,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="revenue.other",
        description="Annual non-milk income (cattle, lamb, wool, other).",
        input_model=OtherRevenueInput,
        handler=_handle_other_revenue,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="revenue.total",
        description="Annual total revenue: milk + schemes + other.",
        input_model=TotalRevenueInput,
        handler=_handle_total_revenue,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="costs.total",
        description="Annual total costs. Missing cost lines count as 0.",
        input_model=TotalCostsInput,
        handler=_handle_total_costs,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="profit.net",
        description="Net profit: revenue − costs. Both must already be totals.",
        input_model=ProfitInput,
        handler=_handle_net_profit,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="profit.margin",
        description="Profit margin as a 0–1 ratio and as a percentage.",
        input_model=ProfitInput,
        handler=_handle_profit_margin,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="pl.summary",
        description="Full annual P&L from raw drivers: revenue split, costs, profit, margin.",
        input_model=PlSummaryInput,
        handler=pl_summary,
        supports_provenance=False,
    ),
)

PUBLIC_CALCULATION_IDS: tuple[str, ...] = tuple(c.id for c in CALCULATION_CATALOGUE)

FUNCTIONS: dict[str, CalculationDefinition] = {c.id: c for c in CALCULATION_CATALOGUE}

INPUT_MODELS: dict[str, type[BaseModel]] = {
    c.id: c.input_model for c in CALCULATION_CATALOGUE
}

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    c.id: c.required for c in CALCULATION_CATALOGUE
}

OPTIONAL_FIELDS: dict[str, tuple[str, ...]] = {
    c.id: c.optional for c in CALCULATION_CATALOGUE
}


def get_function(key: str) -> CalculationDefinition | None:
    return FUNCTIONS.get(key)


def list_functions() -> list[dict[str, Any]]:
    """Discovery payload. Field name ``key`` is the public calculation ID."""
    payload = [
        {
            "key": spec.id,
            "description": spec.description,
            "required": list(spec.required),
            "optional": list(spec.optional),
        }
        for spec in CALCULATION_CATALOGUE
    ]
    payload.sort(key=lambda item: item["key"])
    return payload
