"""Explicit input fields, units, and validation metadata for each callable function."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, create_model, model_validator

from farm_functions.dairy.cash_flow import (
    CASH_FLOW_LINES,
    OPERATING_CASH_INFLOW_CATEGORIES,
    OPERATING_CASH_OUTFLOW_CATEGORIES,
)


def _parse_finite_number(value: Any) -> float:
    """Accept any finite int/float (negatives allowed). Reject bool, null, strings, NaN/Inf."""
    if value is None:
        raise ValueError("null is not a valid value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a number")
    number = float(value)
    if not isfinite(number):
        raise ValueError("must be a finite number")
    return number


def _parse_non_negative_number(value: Any) -> float:
    """Accept int/float >= 0. Reject bool, null, strings, NaN/Inf, and negatives."""
    number = _parse_finite_number(value)
    if number < 0:
        raise ValueError("must be greater than or equal to 0")
    return number


NonNegativeNumber = Annotated[float, BeforeValidator(_parse_non_negative_number)]
# Balances (e.g. bank cash) may be negative: an overdraft is a valid position.
SignedNumber = Annotated[float, BeforeValidator(_parse_finite_number)]


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


# ---------------------------------------------------------------------------
# Phase 1 monthly Dairy Cash Flow drivers (ADR-0022 / ADR-0023). Explicit cash
# amounts for the statement month — not P&L accruals. Fields are generated from
# Dairy ``CASH_FLOW_LINES`` so the catalogue is declared once. Operating lines
# share P&L category IDs (``feed``, ``milk`` …). Period identity is Domain only.
# Household drawings are a financing outflow (ADR-0030).
# ---------------------------------------------------------------------------

MonthlyDairyCashFlowInput = create_model(
    "MonthlyDairyCashFlowInput",
    __base__=_StrictModel,
    **{name: (NonNegativeNumber, 0) for name in CASH_FLOW_LINES},
)


class CfMonthItemInput(MonthlyDairyCashFlowInput):
    """One month of cash lines plus period identity (``cf.months`` item)."""

    year: CalendarYear
    month: CalendarMonth


class CfMonthlyInput(CfMonthItemInput):
    """Flat HTTP / runner input for ``cf.monthly`` (ADR-0022 / ADR-0024).

    Application peels ``year`` / ``month`` into ``MonthlyPeriodIdentity`` and
    the cash lines into ``MonthlyDairyCashFlowInput``. Optional
    ``opening_cash`` (may be negative) adds ``closing_cash`` to the result.
    """

    opening_cash: SignedNumber | None = None


class CfMonthsInput(_StrictModel):
    """HTTP / runner input for ``cf.months`` (ADR-0024).

    ``opening_cash`` is the bank position at the start of the first month; each
    later month opens with the previous month's closing cash. Months must be
    consecutive (any input order; sorted chronologically).
    """

    opening_cash: SignedNumber
    months: list[CfMonthItemInput] = Field(..., min_length=1)


def _parse_rate_ratio(value: Any) -> float:
    """Annual rate as a 0–1 ratio (0.042 = 4.2%). Rejects percent-style 4.2."""
    number = _parse_non_negative_number(value)
    if number > 1:
        raise ValueError("must be between 0 and 1")
    return number


def _parse_loan_months(value: Any) -> int:
    """Whole number of monthly instalments, 1–600 (50 years)."""
    number = _parse_finite_number(value)
    if not number.is_integer() or not 1 <= number <= 600:
        raise ValueError("must be a whole number between 1 and 600")
    return int(number)


class LoanItemInput(_StrictModel):
    """One loan inside ``loan.schedule`` (ADR-0025).

    State-based: the loan as it stands today. ``year`` / ``month`` is the
    calendar month of the next instalment.
    """

    balance: NonNegativeNumber
    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)]
    remaining_months: Annotated[int, BeforeValidator(_parse_loan_months)]
    year: CalendarYear
    month: CalendarMonth
    original_principal: NonNegativeNumber | None = None

    @model_validator(mode="after")
    def _principal_covers_balance(self) -> "LoanItemInput":
        if self.original_principal is not None and self.original_principal < self.balance:
            raise ValueError("original_principal must be greater than or equal to balance")
        return self


class LoanScheduleInput(_StrictModel):
    """HTTP / runner input for ``loan.schedule``: one or more loans, results in input order."""

    loans: list[LoanItemInput] = Field(..., min_length=1, max_length=50)


class PlMonthlyInput(MonthlyDairyFinancialInput):
    """Flat HTTP / runner input for ``pl.monthly`` (ADR-0019).

    Transport includes period identity; Application peels ``year`` / ``month``
    into ``MonthlyPeriodIdentity`` and the remaining drivers into
    ``MonthlyDairyFinancialInput``.
    """

    year: CalendarYear
    month: CalendarMonth


class PlMonthItemInput(PlMonthlyInput):
    """One month item inside ``pl.months`` (same fields as ``pl.monthly``)."""


class PlMonthsYtdInput(_StrictModel):
    """Optional YTD identity for ``pl.months`` (ADR-0021)."""

    year: CalendarYear
    as_of_month: CalendarMonth


class PlMonthsInput(_StrictModel):
    """HTTP / runner input for ``pl.months`` (ADR-0021).

    Nested ``months`` array (each item = ``pl.monthly`` fields). Optional ``ytd``
    requests Domain YTD aggregation; omit or JSON ``null`` for months-only.
    """

    months: list[PlMonthItemInput] = Field(..., min_length=1)
    ytd: PlMonthsYtdInput | None = None


def _reject_duplicate_months(items: list[Any]) -> None:
    seen: set[tuple[int, int]] = set()
    for item in items:
        key = (item.year, item.month)
        if key in seen:
            raise ValueError(f"duplicate monthly period year={key[0]} month={key[1]}")
        seen.add(key)


class PlCompareInput(_StrictModel):
    """HTTP / runner input for ``pl.compare`` (ADR-0035): actual vs comparison
    months (prior year or budget), each in pl.months item shape."""

    actual: list[PlMonthItemInput] = Field(..., min_length=1)
    comparison: list[PlMonthItemInput] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "PlCompareInput":
        _reject_duplicate_months(self.actual)
        _reject_duplicate_months(self.comparison)
        return self


class CfCompareInput(_StrictModel):
    """HTTP / runner input for ``cf.compare`` (ADR-0035); cf.months item shape."""

    actual: list[CfMonthItemInput] = Field(..., min_length=1)
    comparison: list[CfMonthItemInput] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "CfCompareInput":
        _reject_duplicate_months(self.actual)
        _reject_duplicate_months(self.comparison)
        return self


class KpiSummaryInput(_StrictModel):
    """HTTP / runner input for ``kpi.summary`` (ADR-0028): the pl.months items
    for the period plus the average milking herd over it."""

    months: list[PlMonthItemInput] = Field(..., min_length=1)
    milking_cows: NonNegativeNumber
    # Optional period totals (ADR-0032).
    milk_solids_kg: NonNegativeNumber | None = None
    hectares: NonNegativeNumber | None = None
    debt_balance: NonNegativeNumber | None = None


def _parse_pct_change(value: Any) -> float:
    """Percentage change; -100 (line goes to 0) or greater."""
    number = _parse_finite_number(value)
    if number < -100:
        raise ValueError("must be -100 or greater")
    return number


PctChange = Annotated[float, BeforeValidator(_parse_pct_change)]

# Lines a scenario may shock by %. Milk has dedicated price / volume shocks.
SHOCKABLE_LINES = tuple(
    sorted(
        (set(MonthlyDairyFinancialInput.model_fields) | set(CASH_FLOW_LINES))
        - {"milk_litres", "milk_price", "milk"}
    )
)


# Operating lines an investment can change by a monthly EUR amount (ADR-0031).
EFFECT_LINES = tuple(
    line
    for activity_lines in (OPERATING_CASH_INFLOW_CATEGORIES, OPERATING_CASH_OUTFLOW_CATEGORIES)
    for line in activity_lines
    if line != "milk"
)


class InvestmentLoanInput(_StrictModel):
    """Loan drawn for an investment; first instalment the month after purchase."""

    amount: NonNegativeNumber
    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)]
    remaining_months: Annotated[int, BeforeValidator(_parse_loan_months)]


class InvestmentInput(_StrictModel):
    """A capital purchase inside a scenario (ADR-0031)."""

    year: CalendarYear
    month: CalendarMonth
    amount: NonNegativeNumber
    cash_line: Literal["machinery_equipment_payments", "other_capital_payments"] = (
        "other_capital_payments"
    )
    loan: InvestmentLoanInput | None = None
    monthly_effects: dict[str, SignedNumber] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _known_effect_lines(self) -> "InvestmentInput":
        unknown = sorted(set(self.monthly_effects) - set(EFFECT_LINES))
        if unknown:
            raise ValueError(
                f"monthly_effects has lines that cannot be changed: {', '.join(unknown)}"
            )
        return self


class SensitivityScenarioInput(_StrictModel):
    """One what-if: milk price c/L, milk volume %, herd size %, % per line, investments."""

    name: str | None = Field(None, max_length=40)
    milk_price_c: SignedNumber = 0.0
    milk_volume_pct: PctChange = 0.0
    herd_pct: PctChange = 0.0
    lines_pct: dict[str, PctChange] = Field(default_factory=dict)
    investments: list[InvestmentInput] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _known_lines(self) -> "SensitivityScenarioInput":
        unknown = sorted(set(self.lines_pct) - set(SHOCKABLE_LINES))
        if unknown:
            raise ValueError(f"lines_pct has lines that cannot be shocked: {', '.join(unknown)}")
        return self


class RiskSensitivityInput(_StrictModel):
    """HTTP / runner input for ``risk.sensitivity`` (ADR-0029).

    ``pl_months`` drive surplus / DSCR / milk price; ``cf_months`` (consecutive)
    and ``opening_cash`` drive the cash balance. Both actual + projected.
    """

    pl_months: list[PlMonthItemInput] = Field(..., min_length=1)
    cf_months: list[CfMonthItemInput] = Field(..., min_length=1)
    opening_cash: SignedNumber
    scenarios: list[SensitivityScenarioInput] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _investments_inside_cash_months(self) -> "RiskSensitivityInput":
        months = {(m.year, m.month) for m in self.cf_months}
        for scenario in self.scenarios:
            for inv in scenario.investments:
                if (inv.year, inv.month) not in months:
                    raise ValueError(
                        f"investment month year={inv.year} month={inv.month} is outside cf_months"
                    )
        return self


# ---------------------------------------------------------------------------
# Forecast inputs (ADR-0026). ``history`` = actual months (pl.months / cf.months
# item shape). ``forecast`` items carry period identity plus optional known
# values; an omitted (or null) line is projected.
# ---------------------------------------------------------------------------


def _forecast_item_model(name: str, lines: tuple[str, ...]) -> type[BaseModel]:
    return create_model(
        name,
        __base__=_StrictModel,
        year=(CalendarYear, ...),
        month=(CalendarMonth, ...),
        **{line: (NonNegativeNumber | None, None) for line in lines},
    )


def _check_forecast_periods(history: list[Any], forecast: list[Any]) -> None:
    """Unique periods, forecast after history, prior-year month present."""
    for items in (history, forecast):
        seen: set[tuple[int, int]] = set()
        for item in items:
            key = (item.year, item.month)
            if key in seen:
                raise ValueError(f"duplicate monthly period year={key[0]} month={key[1]}")
            seen.add(key)
    actual = {(item.year, item.month) for item in history}
    last = max(actual)
    for item in forecast:
        if (item.year, item.month) <= last:
            raise ValueError(
                f"forecast month year={item.year} month={item.month} must be after "
                f"the last history month year={last[0]} month={last[1]}"
            )
        if (item.year - 1, item.month) not in actual:
            raise ValueError(
                f"forecast needs prior-year history for year={item.year - 1} month={item.month}"
            )


PlForecastItemInput = _forecast_item_model(
    "PlForecastItemInput", tuple(MonthlyDairyFinancialInput.model_fields)
)


class PlForecastInput(_StrictModel):
    """HTTP / runner input for ``pl.forecast`` (ADR-0026)."""

    history: list[PlMonthItemInput] = Field(..., min_length=1)
    forecast: list[PlForecastItemInput] = Field(..., min_length=1)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _periods(self) -> "PlForecastInput":
        _check_forecast_periods(self.history, self.forecast)
        return self


CfForecastItemInput = _forecast_item_model("CfForecastItemInput", CASH_FLOW_LINES)


class CfForecastInput(_StrictModel):
    """HTTP / runner input for ``cf.forecast`` (ADR-0026)."""

    history: list[CfMonthItemInput] = Field(..., min_length=1)
    forecast: list[CfForecastItemInput] = Field(..., min_length=1)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _periods(self) -> "CfForecastInput":
        _check_forecast_periods(self.history, self.forecast)
        return self


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


# Cash position units for ``cf.monthly`` / ``cf.months`` needs_input.
CASH_POSITION_FIELD_UNITS: dict[str, str] = {"opening_cash": "EUR"}

# Loan state units for ``loan.schedule`` needs_input (ADR-0025).
LOAN_FIELD_UNITS: dict[str, str] = {
    "balance": "EUR",
    "annual_rate": "ratio/year",
    "remaining_months": "months",
    "original_principal": "EUR",
}


def missing_field_entry(field: str) -> dict[str, str]:
    """Canonical needs_input.missing item: {field, unit}."""
    unit = (
        FIELD_UNITS.get(field)
        or PERIOD_IDENTITY_FIELD_UNITS.get(field)
        or CASH_POSITION_FIELD_UNITS.get(field)
        or LOAN_FIELD_UNITS.get(field)
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
