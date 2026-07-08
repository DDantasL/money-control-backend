from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import MonthlyBudget
from app.schemas.transaction import MonthlyBudgetCreate, MonthlyBudgetRead
from app.services.delete_service import delete_budget
from app.services.recurring_contribution_service import ensure_recurring_contributions_for_month

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[MonthlyBudgetRead])
def list_budgets(
    month_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> list[MonthlyBudget]:
    ensure_recurring_contributions_for_month(session, month_year)
    statement = (
        select(MonthlyBudget)
        .where(MonthlyBudget.month_year == month_year)
        .order_by(MonthlyBudget.user_id)
    )
    return list(session.exec(statement).all())


@router.post("", response_model=MonthlyBudgetRead)
def upsert_budget(
    payload: MonthlyBudgetCreate,
    session: Session = Depends(get_session),
) -> MonthlyBudget:
    existing = session.exec(
        select(MonthlyBudget).where(
            MonthlyBudget.user_id == payload.user_id,
            MonthlyBudget.month_year == payload.month_year,
        )
    ).first()

    if existing:
        existing.actual_contribution = payload.actual_contribution
        existing.expected_contribution = Decimal("0.00")
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    budget = MonthlyBudget(
        user_id=payload.user_id,
        month_year=payload.month_year,
        actual_contribution=payload.actual_contribution,
        expected_contribution=Decimal("0.00"),
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=204)
def remove_budget(budget_id: int, session: Session = Depends(get_session)) -> None:
    delete_budget(session, budget_id)
