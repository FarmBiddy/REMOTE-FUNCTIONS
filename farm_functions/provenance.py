"""Structured explainability for annual P&L results. Does not reimplement formulas."""

from pydantic import BaseModel, ConfigDict

from farm_functions.calcs.costs import COST_CATEGORIES, total_costs
from farm_functions.calcs.profit import net_profit, profit_margin
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.domain import FinancialInput, FinancialModel
from farm_functions.schemas import FIELD_UNITS

MONEY_UNIT = "EUR/year"
MARGIN_UNIT = "ratio"

SUPPORTED_CALCULATIONS = (
    "revenue.milk",
    "revenue.schemes",
    "revenue.other",
    "revenue.total",
    "costs.total",
    "profit.net",
    "profit.margin",
)


class ProvenanceInput(BaseModel):
    """One operand used in a calculation, with enough data for a UI/agent explanation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    unit: str


class CalculationProvenance(BaseModel):
    """How one annual P&L output was produced. The calculation functions remain authoritative."""

    model_config = ConfigDict(extra="forbid")

    calculation: str
    value: float
    formula: str
    inputs_used: list[ProvenanceInput]
    unit: str


def _field(name: str, value: float, unit: str | None = None) -> ProvenanceInput:
    return ProvenanceInput(name=name, value=float(value), unit=unit or FIELD_UNITS[name])


def explain_annual_pnl(source: FinancialInput | FinancialModel) -> dict[str, CalculationProvenance]:
    """Build provenance from existing calculation functions. Not part of the HTTP response."""
    inputs = source.inputs if isinstance(source, FinancialModel) else source
    data = inputs.model_dump()

    milk = milk_revenue(data["milking_cows"], data["litres_per_cow"], data["milk_price"])
    schemes = scheme_revenue(
        biss=data["biss"],
        acres=data["acres"],
        other_grants=data["other_grants"],
    )
    other = other_revenue(
        cattle_sales=data["cattle_sales"],
        lamb_sales=data["lamb_sales"],
        wool=data["wool"],
        other=data["other"],
    )
    revenue = total_revenue(
        milking_cows=data["milking_cows"],
        litres_per_cow=data["litres_per_cow"],
        milk_price=data["milk_price"],
        biss=data["biss"],
        acres=data["acres"],
        other_grants=data["other_grants"],
        cattle_sales=data["cattle_sales"],
        lamb_sales=data["lamb_sales"],
        wool=data["wool"],
        other=data["other"],
    )
    cost_kwargs = {name: data[name] for name in COST_CATEGORIES}
    costs = total_costs(**cost_kwargs)
    profit = net_profit(revenue, costs)
    margin = profit_margin(revenue, costs)

    return {
        "revenue.milk": CalculationProvenance(
            calculation="revenue.milk",
            value=milk,
            formula="milking_cows * litres_per_cow * milk_price",
            inputs_used=[
                _field("milking_cows", data["milking_cows"]),
                _field("litres_per_cow", data["litres_per_cow"]),
                _field("milk_price", data["milk_price"]),
            ],
            unit=MONEY_UNIT,
        ),
        "revenue.schemes": CalculationProvenance(
            calculation="revenue.schemes",
            value=schemes,
            formula="biss + acres + other_grants",
            inputs_used=[
                _field("biss", data["biss"]),
                _field("acres", data["acres"]),
                _field("other_grants", data["other_grants"]),
            ],
            unit=MONEY_UNIT,
        ),
        "revenue.other": CalculationProvenance(
            calculation="revenue.other",
            value=other,
            formula="cattle_sales + lamb_sales + wool + other",
            inputs_used=[
                _field("cattle_sales", data["cattle_sales"]),
                _field("lamb_sales", data["lamb_sales"]),
                _field("wool", data["wool"]),
                _field("other", data["other"]),
            ],
            unit=MONEY_UNIT,
        ),
        "revenue.total": CalculationProvenance(
            calculation="revenue.total",
            value=revenue,
            formula="revenue.milk + revenue.schemes + revenue.other",
            inputs_used=[
                _field("revenue.milk", milk, MONEY_UNIT),
                _field("revenue.schemes", schemes, MONEY_UNIT),
                _field("revenue.other", other, MONEY_UNIT),
            ],
            unit=MONEY_UNIT,
        ),
        "costs.total": CalculationProvenance(
            calculation="costs.total",
            value=costs,
            formula=" + ".join(COST_CATEGORIES),
            inputs_used=[_field(name, data[name]) for name in COST_CATEGORIES],
            unit=MONEY_UNIT,
        ),
        "profit.net": CalculationProvenance(
            calculation="profit.net",
            value=profit,
            formula="revenue.total - costs.total",
            inputs_used=[
                _field("revenue.total", revenue, MONEY_UNIT),
                _field("costs.total", costs, MONEY_UNIT),
            ],
            unit=MONEY_UNIT,
        ),
        "profit.margin": CalculationProvenance(
            calculation="profit.margin",
            value=margin,
            formula="(revenue.total - costs.total) / revenue.total if revenue.total > 0 else 0",
            inputs_used=[
                _field("revenue.total", revenue, MONEY_UNIT),
                _field("costs.total", costs, MONEY_UNIT),
            ],
            unit=MARGIN_UNIT,
        ),
    }
