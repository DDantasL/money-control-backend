from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.schemas.dashboard import MonthlyDashboard
from app.services.dashboard_service import build_monthly_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{month_year}", response_model=MonthlyDashboard)
def get_monthly_dashboard(
    month_year: str,
    session: Session = Depends(get_session),
) -> MonthlyDashboard:
    if len(month_year) != 7 or month_year[4] != "-":
        raise HTTPException(status_code=400, detail="month_year deve estar no formato YYYY-MM")

    return build_monthly_dashboard(session, month_year)
