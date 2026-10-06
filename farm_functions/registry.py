"""Authoritative catalogue of public calculation IDs for agents and HTTP clients.

Public IDs (e.g. ``revenue.milk``) are stable contract identifiers. They are set
explicitly on each ``CalculationDefinition`` and are independent of Python
handler, module, or class names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from farm_functions.agriculture.revenue import scheme_revenue
from farm_functions.core.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
from farm_functions.dairy.costs import total_costs
from farm_functions.dairy.revenue import milk_revenue, other_revenue, total_revenue
from farm_functions.dairy.statement import pl_summary
from farm_functions.accounts import bs_summary, pl_net
from farm_functions.assets import assets_schedule
from farm_functions.compare import compare_cf, compare_pl
from farm_functions.forecast import forecast_cf, forecast_pl
from farm_functions.kpis import kpi_summary
from farm_functions.loans import debt_capacity, schedule_loans
from farm_functions.projections import plan_projection
from farm_functions.reports import report_accountant, report_advisor, report_bank
from farm_functions.sensitivity import risk_sensitivity
from farm_functions.domain import (
    MonthlyDairyCashFlowModel,
    MonthlyDairyStatementModel,
    MultiMonthDairyCashFlowModel,
    MonthlyPeriodIdentity,
    MultiMonthDairyStatementModel,
    YtdDairyStatementModel,
    calculate_monthly_dairy_cash_flow,
    calculate_multi_month_dairy_cash_flow,
    calculate_monthly_dairy_statement,
    calculate_multi_month_dairy_statements,
    calculate_ytd_dairy_statement,
)
from farm_functions.schemas import (
    AssetsScheduleInput,
    BsSummaryInput,
    CfMonthlyInput,
    CfCompareInput,
    CfForecastInput,
    CfMonthsInput,
    FarmReportInput,
    DebtCapacityInput,
    KpiSummaryInput,
    RiskSensitivityInput,
    LoanScheduleInput,
    MilkRevenueInput,
    MonthlyDairyCashFlowInput,
    MonthlyDairyFinancialInput,
    OtherRevenueInput,
    PlMonthlyInput,
    PlCompareInput,
    PlanProjectionInput,
    PlForecastInput,
    PlNetInput,
    PlMonthsInput,
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


def _handle_pl_monthly(*, year: int, month: int, **drivers: Any) -> dict[str, Any]:
    """Assemble Domain monthly envelope; financial maths stay in Dairy/Domain."""
    model = MonthlyDairyStatementModel(
        period=MonthlyPeriodIdentity(year=year, month=month),
        inputs=MonthlyDairyFinancialInput.model_validate(drivers),
    )
    return calculate_monthly_dairy_statement(model).model_dump()


def _cash_month_envelope(
    year: int, month: int, opening_cash: float | None = None, **lines: Any
) -> MonthlyDairyCashFlowModel:
    return MonthlyDairyCashFlowModel(
        period=MonthlyPeriodIdentity(year=year, month=month),
        inputs=MonthlyDairyCashFlowInput.model_validate(lines),
        opening_cash=opening_cash,
    )


def _handle_cf_monthly(**fields: Any) -> dict[str, Any]:
    """Assemble Domain monthly cash envelope; cash maths stay in Dairy/Core."""
    return calculate_monthly_dairy_cash_flow(_cash_month_envelope(**fields)).model_dump()


def _handle_cf_months(*, opening_cash: float, months: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble consecutive cash months; roll-forward lives in Domain."""
    model = MultiMonthDairyCashFlowModel(
        opening_cash=opening_cash,
        months=[_cash_month_envelope(**item) for item in months],
    )
    return calculate_multi_month_dairy_cash_flow(model).model_dump()


def _handle_pl_months(
    *,
    months: list[dict[str, Any]],
    ytd: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble multi-month (+ optional YTD) via Domain; no Application maths."""
    envelopes = [
        MonthlyDairyStatementModel(
            period=MonthlyPeriodIdentity(year=item["year"], month=item["month"]),
            inputs=MonthlyDairyFinancialInput.model_validate(
                {k: v for k, v in item.items() if k not in ("year", "month")}
            ),
        )
        for item in months
    ]
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(months=envelopes)
    )
    ytd_payload: dict[str, Any] | None = None
    if ytd is not None:
        ytd_payload = calculate_ytd_dairy_statement(
            YtdDairyStatementModel(
                year=ytd["year"],
                as_of_month=ytd["as_of_month"],
                months=envelopes,
            )
        ).model_dump()
    return {
        "currency": multi.currency,
        "months": [month.model_dump() for month in multi.months],
        "ytd": ytd_payload,
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
        description="Annual non-milk income (cattle sales, land leasing income, other).",
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
        description=(
            "Annual total operating costs. Missing cost lines count as 0. "
            "Does not include loan repayments."
        ),
        input_model=TotalCostsInput,
        handler=_handle_total_costs,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="profit.net",
        description=(
            "Phase 1 Operating Surplus: operating income − operating costs. "
            "Both must already be totals. Public ID unchanged."
        ),
        input_model=ProfitInput,
        handler=_handle_net_profit,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="profit.margin",
        description=(
            "Phase 1 Operating Surplus margin as a 0–1 ratio and as a percentage."
        ),
        input_model=ProfitInput,
        handler=_handle_profit_margin,
        supports_provenance=True,
    ),
    CalculationDefinition(
        id="pl.summary",
        description=(
            "Canonical Phase 1 annual Operating Statement: operating income, "
            "operating costs, Operating Surplus, and separate finance (loan repayments)."
        ),
        input_model=PlSummaryInput,
        handler=pl_summary,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="pl.monthly",
        description=(
            "Explicit monthly Dairy Operating Statement from period-scoped drivers "
            "(not annual ÷ 12). Operating income, operating costs, Operating Surplus, "
            "and separate finance (loan repayments)."
        ),
        input_model=PlMonthlyInput,
        handler=_handle_pl_monthly,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="pl.months",
        description=(
            "Multiple explicit monthly Dairy Operating Statements, optionally with a "
            "year-to-date Operating Statement through as_of_month (not annual ÷ 12; "
            "YTD margin from YTD totals)."
        ),
        input_model=PlMonthsInput,
        handler=_handle_pl_months,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="cf.monthly",
        description=(
            "Explicit monthly Dairy Cash Flow (not derived from P&L): operating, "
            "investing and financing inflows/outflows, cash in, cash out, net cash flow. "
            "Line IDs match P&L categories."
        ),
        input_model=CfMonthlyInput,
        handler=_handle_cf_monthly,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="cf.months",
        description=(
            "Consecutive monthly Dairy Cash Flows rolled forward from opening_cash: "
            "each month opens with the previous closing cash; period totals and "
            "closing cash."
        ),
        input_model=CfMonthsInput,
        handler=_handle_cf_months,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="loan.schedule",
        description=(
            "Loan amortisation from today's state for one or more loans: equal monthly "
            "instalments, interest / principal per month, % repaid; portfolio totals and "
            "combined monthly debt service (the cash-flow interest_paid and "
            "loan_principal_repayments lines)."
        ),
        input_model=LoanScheduleInput,
        handler=schedule_loans,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="assets.schedule",
        description=(
            "Fixed asset register over a period: straight-line or reducing-balance "
            "depreciation from the acquisition month; opening NBV + additions − "
            "depreciation = closing NBV per asset, per category and in total."
        ),
        input_model=AssetsScheduleInput,
        handler=assets_schedule,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="debt.capacity",
        description=(
            "Repayment capacity (Operating Surplus + off-farm income − drawings − tax) "
            "over the months sent, cover of current debt service, and the largest new "
            "loan affordable at a rate, term and required cover (inverse annuity)."
        ),
        input_model=DebtCapacityInput,
        handler=debt_capacity,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="kpi.summary",
        description=(
            "Dairy KPIs over the given months (actual or projected): revenue, costs, "
            "each cost line and Operating Surplus in cents per litre; litres, revenue, "
            "costs and surplus per cow; debt service cover ratio (Operating Surplus / "
            "loan repayments). Undefined ratios are null."
        ),
        input_model=KpiSummaryInput,
        handler=kpi_summary,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="pl.net",
        description=(
            "Net profit before tax bridge: Operating Surplus ± livestock and stock "
            "valuation changes − depreciation − interest, with EBIT and net margin. "
            "Depreciation and interest come from assets.schedule / loan.schedule."
        ),
        input_model=PlNetInput,
        handler=pl_net,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="bs.summary",
        description=(
            "Balance sheet at month end: current and non-current assets (fixed asset "
            "NBV from the register) and liabilities (loans split into due within / "
            "after 12 months), net worth, equity %, debt-to-assets %, current ratio, "
            "working capital."
        ),
        input_model=BsSummaryInput,
        handler=bs_summary,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="pl.compare",
        description=(
            "P&L variance: actual months vs comparison months (prior year or budget). "
            "Every line with actual, comparison, change and change %; margin change in "
            "points; milk revenue change split into volume and price effects."
        ),
        input_model=PlCompareInput,
        handler=compare_pl,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="cf.compare",
        description=(
            "Cash flow variance: actual months vs comparison months (prior year or "
            "budget). Every cash line, section and total with change and change %."
        ),
        input_model=CfCompareInput,
        handler=compare_cf,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="risk.sensitivity",
        description=(
            "What-if scenarios over actual + projected months: milk price (c/L), milk "
            "volume % and % per line; surplus, DSCR, closing and lowest cash, overdraft "
            "months per scenario; milk-price break-evens for surplus and for cash."
        ),
        input_model=RiskSensitivityInput,
        handler=risk_sensitivity,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="report.bank",
        description=(
            "Bank report bundle from the farm file: net profit, KPIs incl. DSCR, loans, "
            "repayment / borrowing capacity, balance sheet, actual and projected cash."
        ),
        input_model=FarmReportInput,
        handler=report_bank,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="report.advisor",
        description=(
            "Advisor report bundle from the farm file: KPIs, net profit, variance vs "
            "prior year, what-if scenarios (from the first projected month when sent)."
        ),
        input_model=FarmReportInput,
        handler=report_advisor,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="report.accountant",
        description=(
            "Accountant report bundle from the farm file: P&L by line, net profit before "
            "tax, fixed asset note, balance sheet, cash flow by line with balances."
        ),
        input_model=FarmReportInput,
        handler=report_accountant,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="plan.projection",
        description=(
            "Multi-year annual projection (1–10 years) from the last 12 actual months "
            "and optional per-year assumptions: P&L, net profit, cash rolled forward, "
            "debt and DSCR, simplified balance sheet, KPIs and flags per year."
        ),
        input_model=PlanProjectionInput,
        handler=plan_projection,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="pl.forecast",
        description=(
            "Projected monthly Dairy Operating Statements: same month last year × "
            "year-to-date run-rate per line; milk price carries the latest actual; "
            "known values on a forecast month override. Returns run-rate factors."
        ),
        input_model=PlForecastInput,
        handler=forecast_pl,
        supports_provenance=False,
    ),
    CalculationDefinition(
        id="cf.forecast",
        description=(
            "Projected monthly Dairy Cash Flows: operating lines from same month last "
            "year × run-rate; investing / financing only when given (e.g. "
            "loan.schedule rows). Projected inputs plug into cf.months."
        ),
        input_model=CfForecastInput,
        handler=forecast_cf,
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
