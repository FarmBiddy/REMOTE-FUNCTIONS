"""In-memory P&L domain types. Not persisted; not the HTTP surface.

Annual types (``FinancialInput`` / ``FinancialModel`` / ``FinancialResult``) remain
the Phase 1 annual facade aligned with ``pl.summary``.

Monthly types (ADR-0018 / P1.2): period identity on the envelope; financial
drivers on ``MonthlyDairyFinancialInput``; calculation via
``calculate_monthly_dairy_statement``. Public HTTP ID ``pl.monthly`` (ADR-0019)
assembles this envelope from a flat transport payload.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from farm_functions.dairy.monthly_statement import monthly_pl_summary
from farm_functions.dairy.statement import pl_summary
from farm_functions.schemas import MonthlyDairyFinancialInput, PlSummaryInput

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
