from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.schemas.recurring_contribution import (
    RecurringContributionCreate,
    RecurringContributionRead,
    RecurringContributionUpdate,
)
from app.services.recurring_contribution_service import (
    create_recurring_contribution,
    delete_recurring_contribution,
    ensure_recurring_contributions_for_month,
    get_recurring_contribution,
    list_recurring_contributions,
    update_recurring_contribution,
)

router = APIRouter(prefix="/recurring-contributions", tags=["recurring-contributions"])


@router.get("", response_model=list[RecurringContributionRead])
def get_recurring_contributions(
    session: Session = Depends(get_session),
) -> list[RecurringContributionRead]:
    return [
        RecurringContributionRead.model_validate(item)
        for item in list_recurring_contributions(session)
    ]


@router.get("/{contribution_id}", response_model=RecurringContributionRead)
def get_recurring_contribution_by_id(
    contribution_id: int,
    session: Session = Depends(get_session),
) -> RecurringContributionRead:
    return RecurringContributionRead.model_validate(
        get_recurring_contribution(session, contribution_id)
    )


@router.post("", response_model=RecurringContributionRead, status_code=201)
def create_recurring_contribution_route(
    payload: RecurringContributionCreate,
    month_year: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> RecurringContributionRead:
    contribution = create_recurring_contribution(session, payload)
    if month_year:
        ensure_recurring_contributions_for_month(session, month_year)
        contribution = get_recurring_contribution(session, contribution.id)
    return RecurringContributionRead.model_validate(contribution)


@router.patch("/{contribution_id}", response_model=RecurringContributionRead)
def patch_recurring_contribution(
    contribution_id: int,
    payload: RecurringContributionUpdate,
    session: Session = Depends(get_session),
) -> RecurringContributionRead:
    return RecurringContributionRead.model_validate(
        update_recurring_contribution(session, contribution_id, payload)
    )


@router.delete("/{contribution_id}", status_code=204)
def remove_recurring_contribution(
    contribution_id: int,
    session: Session = Depends(get_session),
) -> None:
    delete_recurring_contribution(session, contribution_id)
