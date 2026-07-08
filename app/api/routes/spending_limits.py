from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import SpendingLimit
from app.schemas.transaction import (
    SpendingLimitCreate,
    SpendingLimitRead,
    SpendingLimitUpdate,
)
from app.services.delete_service import delete_spending_limit
from app.services.update_service import update_spending_limit

router = APIRouter(prefix="/spending-limits", tags=["spending-limits"])


@router.get("", response_model=list[SpendingLimitRead])
def list_spending_limits(
    month_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> list[SpendingLimit]:
    statement = (
        select(SpendingLimit)
        .where(SpendingLimit.month_year == month_year)
        .order_by(SpendingLimit.id)
    )
    return list(session.exec(statement).all())


@router.post("", response_model=SpendingLimitRead, status_code=201)
def upsert_spending_limit(
    payload: SpendingLimitCreate,
    session: Session = Depends(get_session),
) -> SpendingLimit:
    existing = session.exec(
        select(SpendingLimit).where(
            SpendingLimit.month_year == payload.month_year,
            SpendingLimit.category == payload.category,
        )
    ).first()

    if existing:
        existing.limit_value = payload.limit_value
        existing.user_id = payload.user_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    limit = SpendingLimit.model_validate(payload)
    session.add(limit)
    session.commit()
    session.refresh(limit)
    return limit


@router.patch("/{limit_id}", response_model=SpendingLimitRead)
def patch_spending_limit(
    limit_id: int,
    payload: SpendingLimitUpdate,
    session: Session = Depends(get_session),
) -> SpendingLimit:
    return update_spending_limit(session, limit_id, payload)


@router.delete("/{limit_id}", status_code=204)
def remove_spending_limit(limit_id: int, session: Session = Depends(get_session)) -> None:
    delete_spending_limit(session, limit_id)
