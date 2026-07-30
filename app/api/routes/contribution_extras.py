from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.schemas.contribution_extra import ContributionExtraCreate, ContributionExtraRead
from app.services.contribution_extra_service import (
    create_contribution_extra,
    delete_contribution_extra,
    list_contribution_extras,
)

router = APIRouter(prefix="/contribution-extras", tags=["contribution-extras"])


@router.get("", response_model=list[ContributionExtraRead])
def list_extras(
    month_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> list[ContributionExtraRead]:
    return list_contribution_extras(session, month_year)


@router.post("", response_model=ContributionExtraRead)
def add_extra(
    payload: ContributionExtraCreate,
    session: Session = Depends(get_session),
) -> ContributionExtraRead:
    return create_contribution_extra(session, payload)


@router.delete("/{extra_id}", status_code=204)
def remove_extra(extra_id: int, session: Session = Depends(get_session)) -> None:
    delete_contribution_extra(session, extra_id)
