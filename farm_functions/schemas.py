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


# Request size limits (ADR-0050): month lists cover at most 10 years.
MAX_MONTHS = 120


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
    months: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)


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
    # Variable-rate loans follow interest-rate shocks (ADR-0043); fixed ones do not.
    variable: bool = False

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

    months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
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

    actual: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    comparison: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)

    @model_validator(mode="after")
    def _unique(self) -> "PlCompareInput":
        _reject_duplicate_months(self.actual)
        _reject_duplicate_months(self.comparison)
        return self


class CfCompareInput(_StrictModel):
    """HTTP / runner input for ``cf.compare`` (ADR-0035); cf.months item shape."""

    actual: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    comparison: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)

    @model_validator(mode="after")
    def _unique(self) -> "CfCompareInput":
        _reject_duplicate_months(self.actual)
        _reject_duplicate_months(self.comparison)
        return self


def _parse_cover(value: Any) -> float:
    """Required debt cover multiple: 1 or more (1.25 = 25% headroom)."""
    number = _parse_finite_number(value)
    if number < 1:
        raise ValueError("must be 1 or greater")
    return number


class DebtCapacityInput(_StrictModel):
    """HTTP / runner input for ``debt.capacity`` (ADR-0036).

    ``months``: the assessment period (pl.months items, actual or projected).
    ``drawings`` / ``tax`` / ``off_farm_income``: totals for the same period.
    """

    months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)]
    term_months: Annotated[int, BeforeValidator(_parse_loan_months)]
    drawings: NonNegativeNumber = 0.0
    tax: NonNegativeNumber = 0.0
    off_farm_income: NonNegativeNumber = 0.0
    min_cover: Annotated[float, BeforeValidator(_parse_cover)] = 1.0

    @model_validator(mode="after")
    def _unique(self) -> "DebtCapacityInput":
        _reject_duplicate_months(self.months)
        return self


class PlNetInput(_StrictModel):
    """HTTP / runner input for ``pl.net`` (ADR-0038): months + period totals.

    ``depreciation`` from ``assets.schedule``, ``interest`` from ``loan.schedule``
    rows; livestock / stock values are Platform valuations at period start / end.
    """

    months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    depreciation: NonNegativeNumber = 0.0
    interest: NonNegativeNumber = 0.0
    livestock_opening_value: NonNegativeNumber = 0.0
    livestock_closing_value: NonNegativeNumber = 0.0
    stock_opening_value: NonNegativeNumber = 0.0
    stock_closing_value: NonNegativeNumber = 0.0

    @model_validator(mode="after")
    def _unique(self) -> "PlNetInput":
        _reject_duplicate_months(self.months)
        return self


class AssetInput(_StrictModel):
    """One fixed asset in the register (ADR-0037). ``year`` / ``month`` = acquired."""

    category: Literal["machinery", "buildings", "other"] = "machinery"
    cost: NonNegativeNumber
    year: CalendarYear
    month: CalendarMonth
    method: Literal["straight_line", "reducing_balance"] = "straight_line"
    life_months: Annotated[int, BeforeValidator(_parse_loan_months)] | None = None
    residual_value: NonNegativeNumber = 0.0
    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)] | None = None

    @model_validator(mode="after")
    def _method_fields(self) -> "AssetInput":
        if self.method == "straight_line" and self.life_months is None:
            raise ValueError("life_months is required for straight_line")
        if self.method == "reducing_balance" and self.annual_rate is None:
            raise ValueError("annual_rate is required for reducing_balance")
        if self.residual_value > self.cost:
            raise ValueError("residual_value must not exceed cost")
        return self


class BsSummaryInput(_StrictModel):
    """HTTP / runner input for ``bs.summary`` (ADR-0039): balance sheet at the end
    of ``year`` / ``month``. Loans and the asset register use the
    ``loan.schedule`` / ``assets.schedule`` item shapes; other values are
    Platform valuations / balances at that date."""

    year: CalendarYear
    month: CalendarMonth
    cash: SignedNumber = 0.0
    debtors: NonNegativeNumber = 0.0
    stock: NonNegativeNumber = 0.0
    livestock: NonNegativeNumber = 0.0
    land: NonNegativeNumber = 0.0
    creditors: NonNegativeNumber = 0.0
    other_long_term_liabilities: NonNegativeNumber = 0.0
    loans: list[LoanItemInput] = Field(default_factory=list, max_length=50)
    assets: list[AssetInput] = Field(default_factory=list, max_length=200)


class AssetsScheduleInput(_StrictModel):
    """HTTP / runner input for ``assets.schedule`` (ADR-0037): register + period."""

    assets: list[AssetInput] = Field(..., min_length=1, max_length=200)
    from_year: CalendarYear
    from_month: CalendarMonth
    to_year: CalendarYear
    to_month: CalendarMonth

    @model_validator(mode="after")
    def _ordered(self) -> "AssetsScheduleInput":
        if (self.to_year, self.to_month) < (self.from_year, self.from_month):
            raise ValueError("period end must not be before period start")
        return self


class KpiSummaryInput(_StrictModel):
    """HTTP / runner input for ``kpi.summary`` (ADR-0028): the pl.months items
    for the period plus the average milking herd over it."""

    months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
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
    # Percentage points added to variable-rate loans in ``loans`` (ADR-0043).
    rate_shift_pp: SignedNumber = 0.0
    lines_pct: dict[str, PctChange] = Field(default_factory=dict)
    investments: list[InvestmentInput] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def _known_lines(self) -> "SensitivityScenarioInput":
        unknown = sorted(set(self.lines_pct) - set(SHOCKABLE_LINES))
        if unknown:
            raise ValueError(f"lines_pct has lines that cannot be shocked: {', '.join(unknown)}")
        return self


class _RiskBaseInput(_StrictModel):
    """Months, cash, loans and shock start shared by the risk IDs.

    ``pl_months`` drive surplus / DSCR / milk price; ``cf_months`` (consecutive)
    and ``opening_cash`` drive the cash balance. Both actual + projected.
    """

    pl_months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    cf_months: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    opening_cash: SignedNumber
    # Loans behind the months' loan lines; variable ones follow rate shocks (ADR-0043).
    loans: list[LoanItemInput] = Field(default_factory=list, max_length=50)
    # Optional: shocks apply from this month on; earlier months are history (ADR-0040).
    shocks_from_year: CalendarYear | None = None
    shocks_from_month: CalendarMonth | None = None

    @model_validator(mode="after")
    def _shock_start_pair(self) -> "_RiskBaseInput":
        if (self.shocks_from_year is None) != (self.shocks_from_month is None):
            raise ValueError("shocks_from_year and shocks_from_month must be sent together")
        return self


class RiskSensitivityInput(_RiskBaseInput):
    """HTTP / runner input for ``risk.sensitivity`` (ADR-0029)."""

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


def _parse_step_pct(value: Any) -> float:
    """Tornado step: a % above 0 and at most 100."""
    number = _parse_finite_number(value)
    if not 0 < number <= 100:
        raise ValueError("must be above 0 and at most 100")
    return number


class RiskTornadoInput(_RiskBaseInput):
    """HTTP / runner input for ``risk.tornado`` (ADR-0044)."""

    step_pct: Annotated[float, BeforeValidator(_parse_step_pct)] = 10.0
    rate_step_pp: Annotated[float, BeforeValidator(_parse_non_negative_number)] = 1.0
    rank_by: Literal["operating_surplus", "closing_cash", "lowest_cash"] = "operating_surplus"


def _parse_life_years(value: Any) -> float:
    """Asset life in years: above 0, at most 100."""
    number = _parse_finite_number(value)
    if not 0 < number <= 100:
        raise ValueError("must be above 0 and at most 100")
    return number


class BudgetItemInput(_StrictModel):
    """One labelled annual amount in a partial budget (ADR-0045)."""

    label: str = Field(..., min_length=1, max_length=60)
    amount: NonNegativeNumber


class CapitalInput(_StrictModel):
    """Capital tied up by the change: charged as depreciation + interest on half."""

    amount: NonNegativeNumber
    life_years: Annotated[float, BeforeValidator(_parse_life_years)]
    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)] = 0.0


class PartialBudgetInput(_StrictModel):
    """HTTP / runner input for ``decision.partial_budget`` (ADR-0045)."""

    added_income: list[BudgetItemInput] = Field(default_factory=list, max_length=30)
    reduced_costs: list[BudgetItemInput] = Field(default_factory=list, max_length=30)
    added_costs: list[BudgetItemInput] = Field(default_factory=list, max_length=30)
    reduced_income: list[BudgetItemInput] = Field(default_factory=list, max_length=30)
    capital: CapitalInput | None = None


def _parse_life_years_whole(value: Any) -> int:
    """Investment life: whole number of years, 1–40."""
    number = _parse_finite_number(value)
    if not number.is_integer() or not 1 <= number <= 40:
        raise ValueError("must be a whole number between 1 and 40")
    return int(number)


class InvestmentAppraisalInput(_StrictModel):
    """HTTP / runner input for ``decision.investment`` (ADR-0046).

    Benefits either as a constant ``annual_benefit`` over ``life_years`` or as
    explicit year-by-year ``cash_flows`` (year 1 first; may be negative).
    """

    amount: NonNegativeNumber
    discount_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)]
    annual_benefit: SignedNumber | None = None
    life_years: Annotated[int, BeforeValidator(_parse_life_years_whole)] | None = None
    cash_flows: list[SignedNumber] = Field(default_factory=list, max_length=40)
    residual_value: NonNegativeNumber = 0.0

    @model_validator(mode="after")
    def _one_benefit_form(self) -> "InvestmentAppraisalInput":
        simple = self.annual_benefit is not None or self.life_years is not None
        if simple == bool(self.cash_flows):
            raise ValueError("send either annual_benefit with life_years, or cash_flows")
        if simple and (self.annual_benefit is None or self.life_years is None):
            raise ValueError("send either annual_benefit with life_years, or cash_flows")
        return self


class NewLoanTermsInput(_StrictModel):
    """Terms of the loan being applied for (``debt.capacity`` in the bank report)."""

    annual_rate: Annotated[float, BeforeValidator(_parse_rate_ratio)]
    term_months: Annotated[int, BeforeValidator(_parse_loan_months)]
    min_cover: Annotated[float, BeforeValidator(_parse_cover)] = 1.0


class FarmReportInput(_StrictModel):
    """Farm file shared by ``report.bank`` / ``report.advisor`` / ``report.accountant``
    (ADR-0041). Reporting period = ``pl_months``; report date = its last month.

    Item shapes reuse the other IDs: ``pl.months``, ``cf.months``,
    ``loan.schedule`` (loans as at the report date), ``assets.schedule``.
    Balances / valuations are at the report date; opening valuations default to
    the closing ones (no change).
    """

    pl_months: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    cf_months: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    opening_cash: SignedNumber
    milking_cows: NonNegativeNumber
    hectares: NonNegativeNumber | None = None
    milk_solids_kg: NonNegativeNumber | None = None
    prior_pl_months: list[PlMonthItemInput] = Field(default_factory=list, max_length=MAX_MONTHS)
    projected_pl_months: list[PlMonthItemInput] = Field(default_factory=list, max_length=MAX_MONTHS)
    projected_cf_months: list[CfMonthItemInput] = Field(default_factory=list, max_length=MAX_MONTHS)
    loans: list[LoanItemInput] = Field(default_factory=list, max_length=50)
    assets: list[AssetInput] = Field(default_factory=list, max_length=200)
    debtors: NonNegativeNumber = 0.0
    stock: NonNegativeNumber = 0.0
    livestock: NonNegativeNumber = 0.0
    land: NonNegativeNumber = 0.0
    creditors: NonNegativeNumber = 0.0
    other_long_term_liabilities: NonNegativeNumber = 0.0
    livestock_opening_value: NonNegativeNumber | None = None
    stock_opening_value: NonNegativeNumber | None = None
    drawings: NonNegativeNumber = 0.0
    tax: NonNegativeNumber = 0.0
    off_farm_income: NonNegativeNumber = 0.0
    new_loan: NewLoanTermsInput | None = None
    scenarios: list[SensitivityScenarioInput] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _aligned(self) -> "FarmReportInput":
        for items in (self.pl_months, self.prior_pl_months, self.projected_pl_months):
            _reject_duplicate_months(items)
        last_pl = max((m.year, m.month) for m in self.pl_months)
        last_cf = max((m.year, m.month) for m in self.cf_months)
        if last_pl != last_cf:
            raise ValueError("cf_months must end in the same month as pl_months")
        for items in (self.projected_pl_months, self.projected_cf_months):
            if items and min((m.year, m.month) for m in items) <= last_pl:
                raise ValueError("projected months must be after the reporting period")
        return self


def _parse_projection_years(value: Any) -> int:
    """Projection horizon: whole number of years, 1–10."""
    number = _parse_finite_number(value)
    if not number.is_integer() or not 1 <= number <= 10:
        raise ValueError("must be a whole number between 1 and 10")
    return int(number)


ProjectionYears = Annotated[int, BeforeValidator(_parse_projection_years)]
# P&L lines a projection may set by amount (milk has price / herd / yield drivers).
PROJECTION_AMOUNT_LINES = tuple(
    line
    for line in MonthlyDairyFinancialInput.model_fields
    if line not in ("milk_litres", "milk_price", "loan_repayments")
)


class ProjectionAssumptionsInput(_StrictModel):
    """Per-year assumption lists (index 0 = year 1); all optional (ADR-0042)."""

    milk_price: list[NonNegativeNumber] = Field(default_factory=list, max_length=10)
    herd_pct: list[PctChange] = Field(default_factory=list, max_length=10)
    yield_pct: list[PctChange] = Field(default_factory=list, max_length=10)
    cost_inflation_pct: list[PctChange] = Field(default_factory=list, max_length=10)
    lines_inflation_pct: dict[str, Annotated[list[PctChange], Field(max_length=10)]] = Field(default_factory=dict)
    lines_amount: dict[str, Annotated[list[NonNegativeNumber], Field(max_length=10)]] = Field(default_factory=dict)
    drawings: list[NonNegativeNumber] = Field(default_factory=list, max_length=10)
    tax: list[NonNegativeNumber] = Field(default_factory=list, max_length=10)
    off_farm_income: list[NonNegativeNumber] = Field(default_factory=list, max_length=10)
    # Percentage points on variable-rate loans vs today, per year; carried (ADR-0043).
    interest_rate_shift_pp: list[SignedNumber] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _known_lines(self) -> "ProjectionAssumptionsInput":
        unknown = sorted(
            (set(self.lines_inflation_pct) - set(OPERATING_CASH_OUTFLOW_CATEGORIES))
            | (set(self.lines_amount) - set(PROJECTION_AMOUNT_LINES))
        )
        if unknown:
            raise ValueError(f"assumptions have unknown lines: {', '.join(unknown)}")
        return self

    def lists(self) -> list[list[float]]:
        return [
            self.milk_price, self.herd_pct, self.yield_pct, self.cost_inflation_pct,
            self.drawings, self.tax, self.off_farm_income, self.interest_rate_shift_pp,
            *self.lines_inflation_pct.values(), *self.lines_amount.values(),
        ]


class ProjectionInvestmentInput(_StrictModel):
    """Capital purchase in the first month of projection ``year`` (ADR-0042)."""

    year: ProjectionYears
    amount: NonNegativeNumber
    life_months: Annotated[int, BeforeValidator(_parse_loan_months)]
    category: Literal["machinery", "buildings", "other"] = "machinery"
    loan: InvestmentLoanInput | None = None
    annual_effects: dict[str, SignedNumber] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _known_effect_lines(self) -> "ProjectionInvestmentInput":
        unknown = sorted(set(self.annual_effects) - set(EFFECT_LINES))
        if unknown:
            raise ValueError(f"annual_effects has lines that cannot be changed: {', '.join(unknown)}")
        return self


class PlanProjectionInput(_StrictModel):
    """HTTP / runner input for ``plan.projection`` (ADR-0042)."""

    base_pl_months: list[PlMonthItemInput] = Field(..., min_length=12, max_length=12)
    opening_cash: SignedNumber
    milking_cows: NonNegativeNumber
    years: ProjectionYears = 5
    assumptions: ProjectionAssumptionsInput = Field(default_factory=ProjectionAssumptionsInput)
    loans: list[LoanItemInput] = Field(default_factory=list, max_length=50)
    assets: list[AssetInput] = Field(default_factory=list, max_length=200)
    investments: list[ProjectionInvestmentInput] = Field(default_factory=list, max_length=10)
    land: NonNegativeNumber = 0.0
    livestock: NonNegativeNumber = 0.0
    min_cover: Annotated[float, BeforeValidator(_parse_cover)] | None = None

    @model_validator(mode="after")
    def _consistent(self) -> "PlanProjectionInput":
        _reject_duplicate_months(self.base_pl_months)
        keys = sorted((m.year, m.month) for m in self.base_pl_months)
        first = keys[0][0] * 12 + keys[0][1]
        if keys[-1][0] * 12 + keys[-1][1] - first != 11:
            raise ValueError("base_pl_months must be 12 consecutive months")
        if any(len(values) > self.years for values in self.assumptions.lists()):
            raise ValueError("assumption lists must not be longer than years")
        if any(inv.year > self.years for inv in self.investments):
            raise ValueError("investment year must be within years")
        return self


class MilkQualityMonthInput(_StrictModel):
    """One monthly milk statement (ADR-0052). SCC / TBC in thousands per ml."""

    year: CalendarYear
    month: CalendarMonth
    milk_litres: NonNegativeNumber
    fat_pct: NonNegativeNumber
    protein_pct: NonNegativeNumber
    scc_k: NonNegativeNumber
    tbc_k: NonNegativeNumber


class BenchmarkInput(_StrictModel):
    """Reference values for one metric (e.g. ICBF top 10% and national average)."""

    top10: NonNegativeNumber | None = None
    average: NonNegativeNumber | None = None


class QualityBenchmarksInput(_StrictModel):
    scc_k: BenchmarkInput | None = None
    tbc_k: BenchmarkInput | None = None
    fat_pct: BenchmarkInput | None = None
    protein_pct: BenchmarkInput | None = None


class QualityBandInput(_StrictModel):
    """Co-op band: up to ``max_k`` (null = open-ended last band) pays ``adjustment_c`` c/L."""

    max_k: NonNegativeNumber | None = None
    adjustment_c: SignedNumber


def _check_bands(bands: list[QualityBandInput]) -> None:
    limits = [b.max_k for b in bands]
    if not bands:
        return
    if limits[-1] is not None or any(m is None for m in limits[:-1]) or limits[:-1] != sorted(limits[:-1]):
        raise ValueError("bands must ascend by max_k and end with one open-ended band")


class QualityPricingInput(_StrictModel):
    """Co-op component price schedule (A + B − C) and quality bands."""

    fat_eur_per_kg: NonNegativeNumber
    protein_eur_per_kg: NonNegativeNumber
    volume_charge_c_per_l: NonNegativeNumber = 0.0
    scc_bands: list[QualityBandInput] = Field(default_factory=list, max_length=10)
    tbc_bands: list[QualityBandInput] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _bands(self) -> "QualityPricingInput":
        _check_bands(self.scc_bands)
        _check_bands(self.tbc_bands)
        return self


class MilkQualityInput(_StrictModel):
    """HTTP / runner input for ``milk.quality`` (ADR-0052)."""

    months: list[MilkQualityMonthInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    milking_cows: NonNegativeNumber | None = None
    hectares: NonNegativeNumber | None = None
    benchmarks: QualityBenchmarksInput | None = None
    pricing: QualityPricingInput | None = None

    @model_validator(mode="after")
    def _unique(self) -> "MilkQualityInput":
        _reject_duplicate_months(self.months)
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

    history: list[PlMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    forecast: list[PlForecastItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)  # type: ignore[valid-type]

    @model_validator(mode="after")
    def _periods(self) -> "PlForecastInput":
        _check_forecast_periods(self.history, self.forecast)
        return self


CfForecastItemInput = _forecast_item_model("CfForecastItemInput", CASH_FLOW_LINES)


class CfForecastInput(_StrictModel):
    """HTTP / runner input for ``cf.forecast`` (ADR-0026)."""

    history: list[CfMonthItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)
    forecast: list[CfForecastItemInput] = Field(..., min_length=1, max_length=MAX_MONTHS)  # type: ignore[valid-type]

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
    "from_year": "year",
    "from_month": "month",
    "to_year": "year",
    "to_month": "month",
}


# Cash position units for ``cf.monthly`` / ``cf.months`` needs_input.
CASH_POSITION_FIELD_UNITS: dict[str, str] = {"opening_cash": "EUR"}

# Loan state units for ``loan.schedule`` needs_input (ADR-0025).
LOAN_FIELD_UNITS: dict[str, str] = {
    "balance": "EUR",
    "annual_rate": "ratio/year",
    "remaining_months": "months",
    "original_principal": "EUR",
    "term_months": "months",
}


# Units for every other input field (ADR-0048). Structural fields say what they
# hold ("list", "object", "text", "choice", "boolean"), so no field is "unknown".
_EUR = "EUR"
OTHER_FIELD_UNITS: dict[str, str] = {
    **{line: _EUR for line in CASH_FLOW_LINES},
    **dict.fromkeys(
        (
            "amount", "annual_benefit", "cash", "cost", "creditors", "debt_balance", "debtors",
            "depreciation", "drawings", "interest", "land", "livestock", "livestock_closing_value",
            "livestock_opening_value", "off_farm_income", "other_long_term_liabilities",
            "residual_value", "stock", "stock_closing_value", "stock_opening_value", "tax",
        ),
        _EUR,
    ),
    **dict.fromkeys(
        ("cost_inflation_pct", "herd_pct", "milk_volume_pct", "step_pct", "yield_pct"), "%"
    ),
    **dict.fromkeys(("rate_shift_pp", "rate_step_pp", "interest_rate_shift_pp"), "percentage points"),
    "discount_rate": "ratio/year",
    "fat_pct": "%",
    "protein_pct": "%",
    "scc_k": "×1000 cells/ml",
    "tbc_k": "×1000 cfu/ml",
    "max_k": "×1000 per ml",
    "adjustment_c": "c/L",
    "volume_charge_c_per_l": "c/L",
    "fat_eur_per_kg": "EUR/kg",
    "protein_eur_per_kg": "EUR/kg",
    "top10": "metric unit",
    "average": "metric unit",
    "benchmarks": "object",
    "pricing": "object",
    "scc_bands": "list",
    "tbc_bands": "list",
    "min_cover": "times",
    "milk_price_c": "c/L",
    "milk_solids_kg": "kg",
    "hectares": "ha",
    "life_months": "months",
    "life_years": "years",
    "years": "years",
    "as_of_month": "month",
    "shocks_from_year": "year",
    "shocks_from_month": "month",
    **dict.fromkeys(
        (
            "actual", "added_costs", "added_income", "assets", "base_pl_months", "cash_flows",
            "cf_months", "comparison", "forecast", "history", "investments", "loans", "months",
            "pl_months", "prior_pl_months", "projected_cf_months", "projected_pl_months",
            "reduced_costs", "reduced_income", "scenarios",
        ),
        "list",
    ),
    **dict.fromkeys(
        (
            "annual_effects", "assumptions", "capital", "lines_amount", "lines_inflation_pct",
            "lines_pct", "loan", "monthly_effects", "new_loan", "ytd",
        ),
        "object",
    ),
    **dict.fromkeys(("label", "name"), "text"),
    **dict.fromkeys(("cash_line", "category", "method", "rank_by"), "choice"),
    "variable": "boolean",
}


def field_unit(field: str) -> str:
    """Unit of an input field by name (single lookup for needs_input and discovery)."""
    return (
        FIELD_UNITS.get(field)
        or PERIOD_IDENTITY_FIELD_UNITS.get(field)
        or CASH_POSITION_FIELD_UNITS.get(field)
        or LOAN_FIELD_UNITS.get(field)
        or MONTHLY_FIELD_UNITS.get(field)
        or OTHER_FIELD_UNITS.get(field)
        or "unknown"
    )


def missing_field_entry(field: str) -> dict[str, str]:
    """Canonical needs_input.missing item: {field, unit}."""
    return {"field": field, "unit": field_unit(field)}


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
