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


def _parse_calendar_year(value: Any) -> int:
    """Accept whole number year ≥ 1. Reject bool, null, strings, non-integers."""
    if value is None:
        raise ValueError("null is not a valid value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    if isinstance(value, float):
        if not isfinite(value) or not value.is_integer():
            raise ValueError("must be a number")
    year = int(value)
    if year < 1:
        raise ValueError("must be a calendar year of 1 or greater")
    return year


def _parse_calendar_month(value: Any) -> int:
    """Accept whole number month 1–12. Reject bool, null, strings, non-integers."""
    if value is None:
        raise ValueError("null is not a valid value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    if isinstance(value, float):
        if not isfinite(value) or not value.is_integer():
            raise ValueError("must be a number")
    month = int(value)
    if month < 1 or month > 12:
        raise ValueError("must be a calendar month from 1 to 12")
    return month


CalendarYear = Annotated[int, BeforeValidator(_parse_calendar_year)]
CalendarMonth = Annotated[int, BeforeValidator(_parse_calendar_month)]


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
    land_leasing_income: NonNegativeNumber = 0
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
    water: NonNegativeNumber = 0
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


class MonthlyMilkRevenueInput(_StrictModel):
    """Monthly milk drivers (D1-B). Do not use annual ``litres_per_cow`` here."""

    milk_litres: NonNegativeNumber
    milk_price: NonNegativeNumber


class MonthlyDairyFinancialInput(
    MonthlyMilkRevenueInput,
    SchemeRevenueInput,
    OtherRevenueInput,
    TotalCostsInput,
    FinanceInput,
):
    """Financial drivers for one monthly Dairy Operating Statement.

    Period identity (``year`` / ``month``) is **not** on this model — it belongs
    on the Domain envelope (ADR-0018). No annual milk fields
    (``milking_cows``, ``litres_per_cow``).
    """


class PlMonthlyInput(MonthlyDairyFinancialInput):
    """Flat HTTP / runner input for ``pl.monthly`` (ADR-0019).

    Transport includes period identity; Application peels ``year`` / ``month``
    into ``MonthlyPeriodIdentity`` and the remaining drivers into
    ``MonthlyDairyFinancialInput``.
    """

    year: CalendarYear
    month: CalendarMonth


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
            "Annual gross proceeds from cattle/calf/cull-cow sales associated "
            "with the Dairy farm (purchases and herd valuation are out of scope)"
        ),
    ),
    InputFieldMetadata(
        name="land_leasing_income",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual income received from leasing owned land out to another party "
            "(operating income; not a capital receipt; not netted against rent_lease)"
        ),
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
        description=(
            "Annual farm electricity expenditure, including pumping electricity "
            "where it is part of the electricity bill"
        ),
    ),
    InputFieldMetadata(
        name="water",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual operating expenditure for farm water supply: water charges/"
            "scheme charges and routine water-system maintenance "
            "(exclude pump electricity — use electricity; exclude water capex)"
        ),
    ),
    InputFieldMetadata(
        name="repairs_maintenance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual general farm repairs and routine maintenance not classified "
            "elsewhere (routine water-system maintenance belongs under water)"
        ),
    ),
    InputFieldMetadata(
        name="rent_lease",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Annual operating cost of land/property rented or leased in "
            "(not income from leasing owned land out)"
        ),
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
        description=(
            "Annual non-water operating levies/charges of the Dairy farm "
            "(water-scheme charges belong under water)"
        ),
    ),
    InputFieldMetadata(
        name="other_operating_costs",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR/year",
        description=(
            "Other annual operating costs that do not belong in another "
            "named category"
        ),
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

# Period identity units for flat HTTP ``pl.monthly`` needs_input (not annual FIELD_UNITS).
PERIOD_IDENTITY_FIELD_UNITS: dict[str, str] = {
    "year": "year",
    "month": "month",
}


def missing_field_entry(field: str) -> dict[str, str]:
    """Canonical needs_input.missing item: {field, unit}."""
    unit = (
        FIELD_UNITS.get(field)
        or PERIOD_IDENTITY_FIELD_UNITS.get(field)
        or MONTHLY_FIELD_UNITS.get(field)
        or "unknown"
    )
    return {"field": field, "unit": unit}


# Monthly Dairy statement financial-driver metadata (ADR-0018). Separate from
# annual INPUT_FIELD_METADATA so FIELD_UNITS / needs_input for pl.summary stay
# annual-only. Period identity (year/month) is Domain envelope metadata, not here.
MONTHLY_DAIRY_INPUT_FIELD_METADATA: tuple[InputFieldMetadata, ...] = (
    InputFieldMetadata(
        name="milk_litres",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="litres",
        description="Milk volume sold/paid in the statement month (not litres/cow/year)",
    ),
    InputFieldMetadata(
        name="milk_price",
        type="number",
        required=True,
        minimum=0,
        maximum=None,
        unit="EUR/litre",
        description="Average EUR/litre for milk in the statement month",
    ),
    InputFieldMetadata(
        name="biss",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="BISS scheme money received in the statement month",
    ),
    InputFieldMetadata(
        name="acres",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="ACRES scheme money (not land area) in the statement month",
    ),
    InputFieldMetadata(
        name="other_grants",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Other operating grants in the statement month",
    ),
    InputFieldMetadata(
        name="cattle_sales",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Cattle sales income in the statement month",
    ),
    InputFieldMetadata(
        name="land_leasing_income",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Income from leasing owned land out in the statement month",
    ),
    InputFieldMetadata(
        name="other",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Other operating income in the statement month",
    ),
    InputFieldMetadata(
        name="feed",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Feed operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="fertiliser",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Fertiliser operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="vet",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Vet operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="contractor",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Contractor operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="labour",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Labour operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="insurance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Insurance operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="fuel",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Fuel operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="electricity",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Electricity operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="water",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Water operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="repairs_maintenance",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Repairs and maintenance operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="rent_lease",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Rent/lease-in operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="professional_fees",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Professional fees operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="levies",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Levies operating cost in the statement month",
    ),
    InputFieldMetadata(
        name="other_operating_costs",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description="Other operating costs in the statement month",
    ),
    InputFieldMetadata(
        name="loan_repayments",
        type="number",
        required=False,
        minimum=0,
        maximum=None,
        unit="EUR",
        description=(
            "Loan repayments in the statement month (finance; does not reduce "
            "Operating Surplus)"
        ),
    ),
)


MONTHLY_FIELD_UNITS: dict[str, str] = {
    item.name: item.unit for item in MONTHLY_DAIRY_INPUT_FIELD_METADATA
}


def list_monthly_dairy_input_metadata() -> list[dict[str, Any]]:
    """Monthly Dairy financial-driver metadata (excludes year/month identity)."""
    return [item.as_dict() for item in MONTHLY_DAIRY_INPUT_FIELD_METADATA]


# Per-calculation REQUIRED_FIELDS / OPTIONAL_FIELDS / INPUT_MODELS are derived
# from farm_functions.registry.CALCULATION_CATALOGUE (authoritative public IDs).
