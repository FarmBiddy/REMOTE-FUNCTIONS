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
    feed: NonNegativeNumber = 0
    fertiliser: NonNegativeNumber = 0
    vet: NonNegativeNumber = 0
    contractor: NonNegativeNumber = 0
    labour: NonNegativeNumber = 0
    insurance: NonNegativeNumber = 0
    loan_repayments: NonNegativeNumber = 0
    fuel: NonNegativeNumber = 0
    electricity: NonNegativeNumber = 0


class ProfitInput(_StrictModel):
    revenue: NonNegativeNumber
    costs: NonNegativeNumber


class PlSummaryInput(TotalRevenueInput, TotalCostsInput):
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
        description="Number of milking cows used in the annual milk revenue calculation",
    ),
    InputFieldMetadata(
        name="litres_per_cow",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="litres/cow/year",
        description="Annual yield per cow used in the annual milk revenue calculation",
    ),
    InputFieldMetadata(
        name="milk_price",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/litre",
        description="Milk price per litre used in the annual milk revenue calculation",
    ),
    InputFieldMetadata(
        name="biss",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual BISS scheme/subsidy amount",
    ),
    InputFieldMetadata(
        name="acres",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual ACRES scheme/subsidy amount in EUR (not land area)",
    ),
    InputFieldMetadata(
        name="other_grants",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual other grant/scheme amount",
    ),
    InputFieldMetadata(
        name="cattle_sales",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual cattle sales amount",
    ),
    InputFieldMetadata(
        name="lamb_sales",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual lamb sales amount",
    ),
    InputFieldMetadata(
        name="wool",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual wool income amount",
    ),
    InputFieldMetadata(
        name="other",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual other non-milk, non-scheme income",
    ),
    InputFieldMetadata(
        name="feed",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual feed cost",
    ),
    InputFieldMetadata(
        name="fertiliser",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual fertiliser cost",
    ),
    InputFieldMetadata(
        name="vet",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual vet cost",
    ),
    InputFieldMetadata(
        name="contractor",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual contractor cost",
    ),
    InputFieldMetadata(
        name="labour",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual labour cost",
    ),
    InputFieldMetadata(
        name="insurance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual insurance cost",
    ),
    InputFieldMetadata(
        name="loan_repayments",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual loan repayment amount included in total costs. "
            "Whether this is principal, interest, or both is not defined"
        ),
    ),
    InputFieldMetadata(
        name="fuel",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual fuel cost",
    ),
    InputFieldMetadata(
        name="electricity",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Annual electricity cost",
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
        description="Already-totalled annual revenue for profit.net and profit.margin",
    ),
    InputFieldMetadata(
        name="costs",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description="Already-totalled annual costs for profit.net and profit.margin",
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
