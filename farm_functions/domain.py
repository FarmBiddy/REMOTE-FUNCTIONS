"""In-memory annual P&L domain types. Not persisted; not the HTTP surface."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from farm_functions.calcs.summary import pl_summary
from farm_functions.schemas import PlSummaryInput

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
