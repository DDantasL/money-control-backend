from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import MonthlyBudget, RecurringContribution, User
from app.schemas.recurring_contribution import (
    RecurringContributionCreate,
    RecurringContributionUpdate,
)


def list_recurring_contributions(session: Session) -> list[RecurringContribution]:
    return list(
        session.exec(
            select(RecurringContribution).order_by(RecurringContribution.user_id)
        ).all()
    )


def get_recurring_contribution(session: Session, contribution_id: int) -> RecurringContribution:
    contribution = session.get(RecurringContribution, contribution_id)
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribuição padrão não encontrada")
    return contribution


def _validate_contributor(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")
    return user


def create_recurring_contribution(
    session: Session,
    payload: RecurringContributionCreate,
) -> RecurringContribution:
    _validate_contributor(session, payload.user_id)

    existing = session.exec(
        select(RecurringContribution).where(RecurringContribution.user_id == payload.user_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Já existe uma contribuição padrão para este contribuinte",
        )

    contribution = RecurringContribution(
        user_id=payload.user_id,
        expected_contribution=payload.expected_contribution,
    )
    session.add(contribution)
    session.commit()
    session.refresh(contribution)
    return contribution


def update_recurring_contribution(
    session: Session,
    contribution_id: int,
    payload: RecurringContributionUpdate,
) -> RecurringContribution:
    contribution = get_recurring_contribution(session, contribution_id)
    contribution.expected_contribution = payload.expected_contribution
    contribution.active = payload.active
    session.add(contribution)
    session.commit()
    session.refresh(contribution)
    return contribution


def delete_recurring_contribution(session: Session, contribution_id: int) -> None:
    contribution = session.get(RecurringContribution, contribution_id)
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribuição padrão não encontrada")

    session.delete(contribution)
    session.commit()


def ensure_recurring_contributions_for_month(session: Session, month_year: str) -> None:
    """Cria contribuições mensais a partir dos padrões ativos que ainda não existem no mês."""
    active_templates = list(
        session.exec(
            select(RecurringContribution).where(RecurringContribution.active.is_(True))
        ).all()
    )

    created = False
    for template in active_templates:
        existing = session.exec(
            select(MonthlyBudget).where(
                MonthlyBudget.user_id == template.user_id,
                MonthlyBudget.month_year == month_year,
            )
        ).first()
        if existing:
            continue

        session.add(
            MonthlyBudget(
                user_id=template.user_id,
                month_year=month_year,
                expected_contribution=Decimal("0.00"),
                actual_contribution=template.expected_contribution,
            )
        )
        created = True

    if created:
        session.commit()
