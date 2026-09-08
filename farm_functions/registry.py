"""Discoverable function catalog for an agent or HTTP client."""

from dataclasses import dataclass
from typing import Any, Callable

from farm_functions.calcs.costs import total_costs
from farm_functions.calcs.profit import net_profit, profit_margin, profit_margin_pct
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.calcs.summary import pl_summary
from farm_functions.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.schemas import OPTIONAL_FIELDS, REQUIRED_FIELDS


@dataclass(frozen=True)
class FunctionSpec:
    key: str
    description: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    handler: Callable[..., Any]


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


FUNCTIONS: dict[str, FunctionSpec] = {
    "revenue.milk": FunctionSpec(
        key="revenue.milk",
        description="Annual milk revenue: cows × litres per cow × price per litre.",
        required=REQUIRED_FIELDS["revenue.milk"],
        optional=OPTIONAL_FIELDS["revenue.milk"],
        handler=_handle_milk_revenue,
    ),
    "revenue.schemes": FunctionSpec(
        key="revenue.schemes",
        description="Annual scheme / subsidy income (BISS, ACRES, other grants).",
        required=REQUIRED_FIELDS["revenue.schemes"],
        optional=OPTIONAL_FIELDS["revenue.schemes"],
        handler=_handle_scheme_revenue,
    ),
    "revenue.other": FunctionSpec(
        key="revenue.other",
        description="Annual non-milk income (cattle, lamb, wool, other).",
        required=REQUIRED_FIELDS["revenue.other"],
        optional=OPTIONAL_FIELDS["revenue.other"],
        handler=_handle_other_revenue,
    ),
    "revenue.total": FunctionSpec(
        key="revenue.total",
        description="Annual total revenue: milk + schemes + other.",
        required=REQUIRED_FIELDS["revenue.total"],
        optional=OPTIONAL_FIELDS["revenue.total"],
        handler=_handle_total_revenue,
    ),
    "costs.total": FunctionSpec(
        key="costs.total",
        description="Annual total costs. Missing cost lines count as 0.",
        required=REQUIRED_FIELDS["costs.total"],
        optional=OPTIONAL_FIELDS["costs.total"],
        handler=_handle_total_costs,
    ),
    "profit.net": FunctionSpec(
        key="profit.net",
        description="Net profit: revenue − costs. Both must already be totals.",
        required=REQUIRED_FIELDS["profit.net"],
        optional=OPTIONAL_FIELDS["profit.net"],
        handler=_handle_net_profit,
    ),
    "profit.margin": FunctionSpec(
        key="profit.margin",
        description="Profit margin as a 0–1 ratio and as a percentage.",
        required=REQUIRED_FIELDS["profit.margin"],
        optional=OPTIONAL_FIELDS["profit.margin"],
        handler=_handle_profit_margin,
    ),
    "pl.summary": FunctionSpec(
        key="pl.summary",
        description="Full annual P&L from raw drivers: revenue split, costs, profit, margin.",
        required=REQUIRED_FIELDS["pl.summary"],
        optional=OPTIONAL_FIELDS["pl.summary"],
        handler=pl_summary,
    ),
}


def get_function(key: str) -> FunctionSpec | None:
    return FUNCTIONS.get(key)


def list_functions() -> list[dict[str, Any]]:
    payload = [
        {
            "key": spec.key,
            "description": spec.description,
            "required": list(spec.required),
            "optional": list(spec.optional),
        }
        for spec in FUNCTIONS.values()
    ]
    payload.sort(key=lambda item: item["key"])
    return payload
