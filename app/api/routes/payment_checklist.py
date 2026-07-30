from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas.payment_checklist import (
    PaymentChecklistRead,
    PaymentChecklistStatus,
    PaymentChecklistUpsert,
)
from app.services.payment_checklist_service import get_checklist_status, upsert_checklist_item

router = APIRouter(prefix="/payment-checklist", tags=["payment-checklist"])


@router.get("/{month_year}", response_model=PaymentChecklistStatus)
def list_checklist_status(
    month_year: str,
    session: Session = Depends(get_session),
) -> PaymentChecklistStatus:
    return get_checklist_status(session, month_year)


@router.put("", response_model=PaymentChecklistRead)
def put_checklist_item(
    payload: PaymentChecklistUpsert,
    session: Session = Depends(get_session),
) -> PaymentChecklistRead:
    item = upsert_checklist_item(session, payload)
    return PaymentChecklistRead(
        id=item.id or 0,
        month_year=item.month_year,
        card_id=item.card_id,
        transaction_id=item.transaction_id,
        checked=item.checked,
    )
