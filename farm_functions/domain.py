"""In-memory financial domain types. Not persisted; not the HTTP surface.

Annual types (``FinancialInput`` / ``FinancialModel`` / ``FinancialResult``) remain
the Phase 1 annual facade aligned with ``pl.summary``.

Monthly types (ADR-0018 / P1.2): period identity on the envelope; financial
drivers on ``MonthlyDairyFinancialInput``; calculation via
``calculate_monthly_dairy_statement``. Public HTTP ID ``pl.monthly`` (ADR-0019)
assembles this envelope from a flat transport payload.

Multi-month (ADR-0020 / P2.1): ``calculate_multi_month_dairy_statements`` composes
the existing monthly calculator over an explicit month list.

YTD (ADR-0020 / P2.2): ``calculate_ytd_dairy_statement`` aggregates contiguous
January–as_of_month results via Core surplus/margin — not annual÷12, not average
monthly margins.

Cash Flow (ADR-0022 / P3.2): ``calculate_monthly_dairy_cash_flow`` composes
explicit monthly cash drivers via Dairy ``monthly_cash_flow`` and Core cash
nets — not derived from P&L.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct
from farm_functions.dairy.cash_flow import monthly_cash_flow
from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES
from farm_functions.dairy.monthly_statement import monthly_pl_summary
from farm_functions.dairy.statement import pl_summary
from farm_functions.schemas import (
    MonthlyDairyCashFlowInput,
    MonthlyDairyFinancialInput,
    PlSummaryInput,
)

Period = Literal["annual"]
Currency = Literal["EUR"]


class FinancialInput(PlSummaryInput):
    """Complete annual P&L drivers for `pl.summary`. Same fields and defaults as PlSummaryInput."""


class FinancialModel(BaseModel):
    """In-memory envelope around annual P&L inputs. This service does not persist it."""

    model_config = ConfigDict(extra="forbid")

    period: Period = "annual"
    currency: Currency = "EUR"
    inputs: FinancialInput


class RevenueResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milk: float
    schemes: float
    other: float
    total: float


class CostLines(BaseModel):
    """Phase 1 operating cost lines. Does not include loan repayments."""

    model_config = ConfigDict(extra="forbid")

    feed: float
    fertiliser: float
    vet: float
    contractor: float
    labour: float
    insurance: float
    fuel: float
    electricity: float
    water: float
    repairs_maintenance: float
    rent_lease: float
    professional_fees: float
    levies: float
    other_operating_costs: float


class CostsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines: CostLines
    total: float


class ProfitResult(BaseModel):
    """Phase 1 Operating Surplus published under stable IDs ``net`` / ``margin``."""

    model_config = ConfigDict(extra="forbid")

    net: float
    margin: float
    margin_pct: float


class FinanceResult(BaseModel):
    """Debt-service amounts reported separately from operating costs."""

    model_config = ConfigDict(extra="forbid")

    loan_repayments: float


class FinancialResult(BaseModel):
    """Structured annual P&L. Shape matches `pl.summary` JSON exactly.

    ``profit.net`` is Phase 1 Operating Surplus (operating income − operating costs).
    Loan repayments appear under ``finance`` and do not reduce Operating Surplus.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    period: Period
    revenue: RevenueResult
    costs: CostsResult
    profit: ProfitResult
    finance: FinanceResult


def calculate_annual_pnl(model: FinancialModel) -> FinancialResult:
    """Run existing `pl.summary` formulas and type the payload as FinancialResult."""
    payload = pl_summary(**model.inputs.model_dump())
    return FinancialResult.model_validate(payload)


class MonthlyPeriodIdentity(BaseModel):
    """Calendar identity for one monthly Operating Statement (ADR-0018 / D2-B).

    Belongs on the Domain envelope — not passed into Core / Agriculture / Dairy
    financial primitives.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["month"] = "month"
    year: int = Field(..., ge=1)
    month: int = Field(..., ge=1, le=12)


class MonthlyDairyStatementModel(BaseModel):
    """In-memory monthly Dairy statement contract (ADR-0018).

    Separates period identity from financial drivers.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency = "EUR"
    period: MonthlyPeriodIdentity
    inputs: MonthlyDairyFinancialInput


class MonthlyDairyStatementResult(BaseModel):
    """Structured monthly Operating Statement (P1.2).

    Reuses annual money component shapes. ``period`` is structured identity
    (not the annual string ``\"annual\"``). ``profit.net`` is Operating Surplus.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    period: MonthlyPeriodIdentity
    revenue: RevenueResult
    costs: CostsResult
    profit: ProfitResult
    finance: FinanceResult


def calculate_monthly_dairy_statement(
    model: MonthlyDairyStatementModel,
) -> MonthlyDairyStatementResult:
    """Compose monthly Operating Statement from explicit monthly drivers.

    Period identity is taken from the envelope (not from Dairy primitives).
    Does not mutate ``model``.
    """
    payload = monthly_pl_summary(**model.inputs.model_dump())
    return MonthlyDairyStatementResult.model_validate(
        {
            "currency": model.currency,
            "period": model.period.model_dump(),
            "revenue": payload["revenue"],
            "costs": payload["costs"],
            "profit": payload["profit"],
            "finance": payload["finance"],
        }
    )


class MultiMonthDairyStatementModel(BaseModel):
    """Explicit collection of monthly envelopes (ADR-0020 / P2.1).

    Not a YTD statement. Sparse and cross-year months are allowed. Duplicate
    ``{year, month}`` identities are rejected. Caller input order does not
    define financial meaning — results are sorted chronologically.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency = "EUR"
    months: list[MonthlyDairyStatementModel] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _reject_duplicate_periods(self) -> "MultiMonthDairyStatementModel":
        seen: set[tuple[int, int]] = set()
        for item in self.months:
            key = (item.period.year, item.period.month)
            if key in seen:
                raise ValueError(
                    f"duplicate monthly period year={key[0]} month={key[1]}"
                )
            seen.add(key)
        return self


class MultiMonthDairyStatementResult(BaseModel):
    """Calculated monthly statements only — no YTD or cross-month totals (P2.1).

    ``months`` are ordered chronologically by ``(year, month)``.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    months: list[MonthlyDairyStatementResult]


def calculate_multi_month_dairy_statements(
    model: MultiMonthDairyStatementModel,
) -> MultiMonthDairyStatementResult:
    """Run existing monthly OS calculation for each explicit month (P2.1).

    Reuses ``calculate_monthly_dairy_statement`` only — no new financial
    formulas, no YTD aggregation. Does not mutate ``model``. Results are
    sorted by ``(period.year, period.month)``.
    """
    results = [calculate_monthly_dairy_statement(month) for month in model.months]
    results.sort(key=lambda r: (r.period.year, r.period.month))
    return MultiMonthDairyStatementResult(currency=model.currency, months=results)


class YtdPeriodIdentity(BaseModel):
    """Identity for a YTD Operating Statement (ADR-0020 / P2.2)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["ytd"] = "ytd"
    year: int = Field(..., ge=1)
    as_of_month: int = Field(..., ge=1, le=12)
    months_included: list[int]


class YtdDairyStatementModel(BaseModel):
    """Explicit months for a named YTD through ``as_of_month`` (ADR-0020 / P2.2).

    All months must share ``year``. January through ``as_of_month`` must all be
    present (contiguous). Same-year months after ``as_of_month`` are allowed on
    the input and ignored for aggregation. Not an annual statement; not ÷12.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency = "EUR"
    year: int = Field(..., ge=1)
    as_of_month: int = Field(..., ge=1, le=12)
    months: list[MonthlyDairyStatementModel] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_ytd_months(self) -> "YtdDairyStatementModel":
        seen: set[int] = set()
        for item in self.months:
            if item.period.year != self.year:
                raise ValueError(
                    f"YTD year={self.year} but month has year={item.period.year} "
                    f"month={item.period.month}"
                )
            month = item.period.month
            if month in seen:
                raise ValueError(
                    f"duplicate monthly period year={self.year} month={month}"
                )
            seen.add(month)
        required = set(range(1, self.as_of_month + 1))
        present_in_window = {m for m in seen if m <= self.as_of_month}
        missing = sorted(required - present_in_window)
        if missing:
            raise ValueError(
                f"YTD through month={self.as_of_month} missing months: {missing}"
            )
        return self


class YtdDairyStatementResult(BaseModel):
    """YTD Operating Statement from explicit contiguous months (P2.2).

    Reuses period-neutral money nests. ``profit.net`` is Operating Surplus from
    YTD income and YTD costs (Core), not the average of monthly margins.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    period: YtdPeriodIdentity
    revenue: RevenueResult
    costs: CostsResult
    profit: ProfitResult
    finance: FinanceResult


def calculate_ytd_dairy_statement(model: YtdDairyStatementModel) -> YtdDairyStatementResult:
    """Aggregate contiguous Jan–as_of_month monthly statements into one YTD OS.

    Runs P2.1 multi-month composition on the filtered window, then Core
    ``sum_amounts`` / ``net_profit`` / margins / publish rounding. Does not
    mutate ``model``. Months after ``as_of_month`` are ignored.
    """
    included = [
        month
        for month in model.months
        if month.period.month <= model.as_of_month
    ]
    multi = calculate_multi_month_dairy_statements(
        MultiMonthDairyStatementModel(currency=model.currency, months=included)
    )
    months = multi.months
    milk = sum_amounts(*(m.revenue.milk for m in months))
    schemes = sum_amounts(*(m.revenue.schemes for m in months))
    other = sum_amounts(*(m.revenue.other for m in months))
    ytd_income = sum_amounts(milk, schemes, other)
    ytd_costs = sum_amounts(*(m.costs.total for m in months))
    cost_lines = {
        name: sum_amounts(*(getattr(m.costs.lines, name) for m in months))
        for name in OPERATING_COST_CATEGORIES
    }
    loans = sum_amounts(*(m.finance.loan_repayments for m in months))
    surplus = net_profit(ytd_income, ytd_costs)
    months_included = sorted(m.period.month for m in months)
    return YtdDairyStatementResult.model_validate(
        {
            "currency": model.currency,
            "period": {
                "kind": "ytd",
                "year": model.year,
                "as_of_month": model.as_of_month,
                "months_included": months_included,
            },
            "revenue": {
                "milk": round_money(milk),
                "schemes": round_money(schemes),
                "other": round_money(other),
                "total": round_money(ytd_income),
            },
            "costs": {
                "lines": {name: round_money(cost_lines[name]) for name in OPERATING_COST_CATEGORIES},
                "total": round_money(ytd_costs),
            },
            "profit": {
                "net": round_money(surplus),
                "margin": round_margin_ratio(profit_margin(ytd_income, ytd_costs)),
                "margin_pct": round_margin_pct(profit_margin_pct(ytd_income, ytd_costs)),
            },
            "finance": {"loan_repayments": round_money(loans)},
        }
    )


# ---------------------------------------------------------------------------
# Cash Flow contracts (ADR-0022 / P3.1) — types only; calculation in P3.2
# ---------------------------------------------------------------------------


class CashLineGroup(BaseModel):
    """Published cash lines for one direction within an activity section."""

    model_config = ConfigDict(extra="forbid")

    lines: dict[str, float]
    total: float


class CashActivitySectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inflows: CashLineGroup
    outflows: CashLineGroup
    net: float


class MonthlyDairyCashFlowModel(BaseModel):
    """In-memory monthly Dairy cash-flow contract (ADR-0022).

    Separates period identity from explicit cash drivers.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency = "EUR"
    period: MonthlyPeriodIdentity
    inputs: MonthlyDairyCashFlowInput


class MonthlyDairyCashFlowResult(BaseModel):
    """Structured monthly Cash Flow statement (P3.2).

    No opening/closing cash yet (D-CF3 → P3.4). ``interest_paid`` appears under
    financing outflows by Phase 1 Dairy catalogue policy, not by Core.
    """

    model_config = ConfigDict(extra="forbid")

    currency: Currency
    period: MonthlyPeriodIdentity
    operating: CashActivitySectionResult
    investing: CashActivitySectionResult
    financing: CashActivitySectionResult
    cash_in: float
    cash_out: float
    net_cash_flow: float


def calculate_monthly_dairy_cash_flow(
    model: MonthlyDairyCashFlowModel,
) -> MonthlyDairyCashFlowResult:
    """Compose monthly Cash Flow from explicit cash drivers.

    Period identity is taken from the envelope (not from Dairy primitives).
    Does not mutate ``model``. Does not derive amounts from P&L.
    """
    payload = monthly_cash_flow(**model.inputs.model_dump())
    return MonthlyDairyCashFlowResult.model_validate(
        {
            "currency": model.currency,
            "period": model.period.model_dump(),
            "operating": payload["operating"],
            "investing": payload["investing"],
            "financing": payload["financing"],
            "cash_in": payload["cash_in"],
            "cash_out": payload["cash_out"],
            "net_cash_flow": payload["net_cash_flow"],
        }
    )
