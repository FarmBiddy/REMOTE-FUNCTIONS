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
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.loans import amortisation_schedule
from farm_functions.core.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
from farm_functions.dairy.costs import total_costs
from farm_functions.dairy.kpis import dairy_kpis
from farm_functions.dairy.revenue import milk_revenue, other_revenue, total_revenue
from farm_functions.dairy.statement import pl_summary
from farm_functions.forecast import forecast_cf, forecast_pl
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
    CfMonthlyInput,
    CfForecastInput,
    CfMonthsInput,
    KpiSummaryInput,
    LoanScheduleInput,
    MilkRevenueInput,
    MonthlyDairyCashFlowInput,
    MonthlyDairyFinancialInput,
    OtherRevenueInput,
    PlMonthlyInput,
    PlForecastInput,
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


def _loan_schedule(
    *,
    balance: float,
    annual_rate: float,
    remaining_months: int,
    year: int,
    month: int,
    original_principal: float | None = None,
) -> dict[str, Any]:
    """One loan: attach calendar periods to Core amortisation rows (ADR-0025)."""
    rows = amortisation_schedule(balance, annual_rate, remaining_months)
    months = []
    for offset, row in enumerate(rows):
        index = year * 12 + month - 1 + offset
        period = {"kind": "month", "year": index // 12, "month": index % 12 + 1}
        months.append({"period": period, **row})
    repaid_pct = None
    if original_principal:
        repaid_pct = round_margin_pct((original_principal - balance) / original_principal * 100)
    return {
        "currency": "EUR",
        "balance": round_money(balance),
        "annual_rate": annual_rate,
        "remaining_months": remaining_months,
        "monthly_payment": rows[0]["payment"],
        "total_interest": round_money(sum(r["interest"] for r in rows)),
        "total_payments": round_money(sum(r["payment"] for r in rows)),
        "repaid_pct": repaid_pct,
        "months": months,
    }


def _handle_loan_schedule(*, loans: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-loan schedules plus portfolio totals and combined monthly debt service."""
    schedules = [_loan_schedule(**loan) for loan in loans]
    combined: dict[tuple[int, int], dict[str, float]] = {}
    for schedule in schedules:
        for row in schedule["months"]:
            key = (row["period"]["year"], row["period"]["month"])
            totals = combined.setdefault(key, {"payment": 0.0, "interest": 0.0, "principal": 0.0})
            for name in totals:
                totals[name] += row[name]
    return {
        "currency": "EUR",
        "loans": schedules,
        "total_balance": round_money(sum(s["balance"] for s in schedules)),
        "total_monthly_payment": round_money(sum(s["monthly_payment"] for s in schedules)),
        "total_interest": round_money(sum(s["total_interest"] for s in schedules)),
        "months": [
            {
                "period": {"kind": "month", "year": year, "month": month},
                **{name: round_money(value) for name, value in totals.items()},
            }
            for (year, month), totals in sorted(combined.items())
        ],
    }


def _handle_kpi_summary(*, months: list[dict[str, Any]], milking_cows: float) -> dict[str, Any]:
    """Run the monthly statements, total them, then derive Dairy KPIs (ADR-0028)."""
    statements = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(
            months=[
                MonthlyDairyStatementModel(
                    period=MonthlyPeriodIdentity(year=item["year"], month=item["month"]),
                    inputs=MonthlyDairyFinancialInput.model_validate(
                        {k: v for k, v in item.items() if k not in ("year", "month")}
                    ),
                )
                for item in months
            ]
        )
    ).model_dump()["months"]

    def total(pick: Callable[[dict[str, Any]], float]) -> float:
        return sum_amounts(*(pick(s) for s in statements))

    totals = {
        "milk_litres": sum_amounts(*(item["milk_litres"] for item in months)),
        "revenue": total(lambda s: s["revenue"]["total"]),
        "costs": total(lambda s: s["costs"]["total"]),
        "surplus": total(lambda s: s["profit"]["net"]),
        "loan_repayments": total(lambda s: s["finance"]["loan_repayments"]),
    }
    cost_lines = {
        name: total(lambda s, name=name: s["costs"]["lines"][name])
        for name in statements[0]["costs"]["lines"]
    }
    return {
        "currency": "EUR",
        "from": statements[0]["period"],
        "to": statements[-1]["period"],
        "month_count": len(statements),
        "milking_cows": milking_cows,
        "totals": {name: round_money(value) for name, value in totals.items()},
        **dairy_kpis(milking_cows=milking_cows, cost_lines=cost_lines, **totals),
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
        handler=_handle_loan_schedule,
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
        handler=_handle_kpi_summary,
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
