from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import MonthlyBudget, User
from app.models.contribution_extra import ContributionExtra
from app.schemas.contribution_extra import ContributionExtraCreate


def list_contribution_extras(session: Session, month_year: str) -> list[ContributionExtra]:
    return list(
        session.exec(
            select(ContributionExtra)
            .where(ContributionExtra.month_year == month_year)
            .order_by(ContributionExtra.created_at.asc(), ContributionExtra.id.asc())
        ).all()
    )


def extras_total_by_user(session: Session, month_year: str) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    for extra in list_contribution_extras(session, month_year):
        totals[extra.user_id] = totals.get(extra.user_id, Decimal("0.00")) + extra.amount
    return totals


def create_contribution_extra(
    session: Session,
    payload: ContributionExtraCreate,
) -> ContributionExtra:
    user = session.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")

    budget = session.exec(
        select(MonthlyBudget).where(
            MonthlyBudget.user_id == payload.user_id,
            MonthlyBudget.month_year == payload.month_year,
        )
    ).first()
    if not budget:
        budget = MonthlyBudget(
            user_id=payload.user_id,
            month_year=payload.month_year,
            expected_contribution=Decimal("0.00"),
            actual_contribution=Decimal("0.00"),
        )
        session.add(budget)
        session.flush()

    extra = ContributionExtra(
        user_id=payload.user_id,
        month_year=payload.month_year,
        amount=payload.amount,
    )
    session.add(extra)
    session.commit()
    session.refresh(extra)
    return extra


def delete_contribution_extra(session: Session, extra_id: int) -> None:
    extra = session.get(ContributionExtra, extra_id)
    if not extra:
        raise HTTPException(status_code=404, detail="Contribuição avulsa não encontrada")
    session.delete(extra)
    session.commit()


def delete_extras_for_user_month(session: Session, user_id: int, month_year: str) -> None:
    extras = session.exec(
        select(ContributionExtra).where(
            ContributionExtra.user_id == user_id,
            ContributionExtra.month_year == month_year,
        )
    ).all()
    for extra in extras:
        session.delete(extra)


def delete_extras_for_user(session: Session, user_id: int) -> None:
    extras = session.exec(
        select(ContributionExtra).where(ContributionExtra.user_id == user_id)
    ).all()
    for extra in extras:
        session.delete(extra)
