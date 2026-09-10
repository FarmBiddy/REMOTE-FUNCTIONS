"""Explicit input fields, units, and validation metadata for each callable function."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _parse_non_negative_number(value: Any) -> float:
    """Accept int/float >= 0. Reject bool, null, strings, NaN/Inf, and negatives."""
    if value is None:
        raise ValueError("null is not a valid value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    number = float(value)
    if not isfinite(number):
        raise ValueError("must be a finite number")
    if number < 0:
        raise ValueError("must be greater than or equal to 0")
    return number


NonNegativeNumber = Annotated[float, BeforeValidator(_parse_non_negative_number)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MilkRevenueInput(_StrictModel):
    milking_cows: NonNegativeNumber
    litres_per_cow: NonNegativeNumber
    milk_price: NonNegativeNumber


class SchemeRevenueInput(_StrictModel):
    biss: NonNegativeNumber = 0
    acres: NonNegativeNumber = 0
    other_grants: NonNegativeNumber = 0


class OtherRevenueInput(_StrictModel):
    cattle_sales: NonNegativeNumber = 0
    lamb_sales: NonNegativeNumber = 0
    wool: NonNegativeNumber = 0
    other: NonNegativeNumber = 0


class TotalRevenueInput(MilkRevenueInput, SchemeRevenueInput, OtherRevenueInput):
    pass


class TotalCostsInput(_StrictModel):
    """Phase 1 operating cost lines. Loan repayments belong on FinanceInput."""

    feed: NonNegativeNumber = 0
    fertiliser: NonNegativeNumber = 0
    vet: NonNegativeNumber = 0
    contractor: NonNegativeNumber = 0
    labour: NonNegativeNumber = 0
    insurance: NonNegativeNumber = 0
    fuel: NonNegativeNumber = 0
    electricity: NonNegativeNumber = 0
    repairs_maintenance: NonNegativeNumber = 0
    rent_lease: NonNegativeNumber = 0
    professional_fees: NonNegativeNumber = 0
    levies: NonNegativeNumber = 0
    other_operating_costs: NonNegativeNumber = 0


class FinanceInput(_StrictModel):
    """Debt-service inputs reported separately from operating costs."""

    loan_repayments: NonNegativeNumber = 0


class ProfitInput(_StrictModel):
    revenue: NonNegativeNumber
    costs: NonNegativeNumber


class PlSummaryInput(TotalRevenueInput, TotalCostsInput, FinanceInput):
    pass


@dataclass(frozen=True)
class InputFieldMetadata:
    name: str
    type: Literal["number", "string"]
    required: bool
    minimum: float | None
    maximum: float | None
    unit: str
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "unit": self.unit,
            "description": self.description,
        }


# Canonical annual P&L input metadata. Units here are the only unit definitions;
# FIELD_UNITS is derived from this list (ADR-0004).
INPUT_FIELD_METADATA: tuple[InputFieldMetadata, ...] = (
    InputFieldMetadata(
        name="milking_cows",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="count",
        description=(
            "Cow count used for the annual milk-income estimate "
            "(Phase 1 Operating Surplus model)"
        ),
    ),
    InputFieldMetadata(
        name="litres_per_cow",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="litres/cow/year",
        description="Litres sold / paid per cow per year used in milk revenue",
    ),
    InputFieldMetadata(
        name="milk_price",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/litre",
        description="Average EUR per litre received for milk",
    ),
    InputFieldMetadata(
        name="biss",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual BISS operating scheme/subsidy income",
    ),
    InputFieldMetadata(
        name="acres",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual ACRES scheme payment in EUR (not land area)",
    ),
    InputFieldMetadata(
        name="other_grants",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Other operating agri-scheme / grant income only "
            "(exclude capital grants and financing)"
        ),
    ),
    InputFieldMetadata(
        name="cattle_sales",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Gross annual cattle sales income "
            "(purchases and herd valuation are out of scope in Phase 1)"
        ),
    ),
    InputFieldMetadata(
        name="lamb_sales",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Gross annual lamb sales income "
            "(purchases and herd valuation are out of scope in Phase 1)"
        ),
    ),
    InputFieldMetadata(
        name="wool",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual wool income",
    ),
    InputFieldMetadata(
        name="other",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Other operating income only "
            "(exclude loans received, capital receipts, asset sales, financing)"
        ),
    ),
    InputFieldMetadata(
        name="feed",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual operating feed cost",
    ),
    InputFieldMetadata(
        name="fertiliser",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual operating fertiliser cost",
    ),
    InputFieldMetadata(
        name="vet",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual veterinary / animal-health operating cost",
    ),
    InputFieldMetadata(
        name="contractor",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual contractor / contract-services operating cost",
    ),
    InputFieldMetadata(
        name="labour",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual paid/hired labour cost only "
            "(do not impute farmer or unpaid family labour)"
        ),
    ),
    InputFieldMetadata(
        name="insurance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual farm operating insurance cost",
    ),
    InputFieldMetadata(
        name="fuel",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual operating fuel cost",
    ),
    InputFieldMetadata(
        name="electricity",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual operating electricity cost",
    ),
    InputFieldMetadata(
        name="repairs_maintenance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual repairs and maintenance operating cost",
    ),
    InputFieldMetadata(
        name="rent_lease",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual land rent / lease operating cost",
    ),
    InputFieldMetadata(
        name="professional_fees",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual professional / accountancy fees (operating)",
    ),
    InputFieldMetadata(
        name="levies",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual levies and similar operating charges",
    ),
    InputFieldMetadata(
        name="other_operating_costs",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Other annual operating costs not covered by named lines",
    ),
    InputFieldMetadata(
        name="loan_repayments",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual loan repayments / debt service. Reported under finance; "
            "does not reduce Phase 1 Operating Surplus. "
            "Principal vs interest is not split"
        ),
    ),
    InputFieldMetadata(
        name="period",
        type="string",
        required=False,
        minimum=None,
        maximum=None,
        unit="annual",
        description='In-memory financial model period. Only "annual" is allowed',
    ),
    InputFieldMetadata(
        name="currency",
        type="string",
        required=False,
        minimum=None,
        maximum=None,
        unit="EUR",
        description='In-memory financial model currency. Only "EUR" is allowed',
    ),
    InputFieldMetadata(
        name="revenue",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Already-totalled annual operating income for profit.net / profit.margin "
            "(Phase 1 Operating Surplus)"
        ),
    ),
    InputFieldMetadata(
        name="costs",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Already-totalled annual operating costs for profit.net / profit.margin "
            "(exclude loan repayments)"
        ),
    ),
)


def list_input_metadata() -> list[dict[str, Any]]:
    """Annual P&L input metadata: name, type, required, min/max, unit, description."""
    return [item.as_dict() for item in INPUT_FIELD_METADATA]


FIELD_UNITS: dict[str, str] = {item.name: item.unit for item in INPUT_FIELD_METADATA}


def missing_field_entry(field: str) -> dict[str, str]:
    """Canonical needs_input.missing item: {field, unit}."""
    return {"field": field, "unit": FIELD_UNITS.get(field, "unknown")}


# Per-calculation REQUIRED_FIELDS / OPTIONAL_FIELDS / INPUT_MODELS are derived
# from farm_functions.registry.CALCULATION_CATALOGUE (authoritative public IDs).
