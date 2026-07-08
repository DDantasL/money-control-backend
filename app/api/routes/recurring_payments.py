from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
from app.models import RecurringPayment
from app.schemas.recurring_payment import (
    RecurringPaymentCreate,
    RecurringPaymentRead,
    RecurringPaymentUpdate,
)
from app.services.recurring_payment_service import (
    create_recurring_payment,
    delete_recurring_payment,
    ensure_recurring_transactions_for_month,
    get_recurring_payment,
    list_recurring_payments,
    update_recurring_payment,
)

router = APIRouter(prefix="/recurring-payments", tags=["recurring-payments"])


@router.get("", response_model=list[RecurringPaymentRead])
def get_recurring_payments(session: Session = Depends(get_session)) -> list[RecurringPaymentRead]:
    return [RecurringPaymentRead.model_validate(payment) for payment in list_recurring_payments(session)]


@router.get("/{payment_id}", response_model=RecurringPaymentRead)
def get_recurring_payment_by_id(
    payment_id: int,
    session: Session = Depends(get_session),
) -> RecurringPaymentRead:
    return RecurringPaymentRead.model_validate(get_recurring_payment(session, payment_id))


@router.post("", response_model=RecurringPaymentRead, status_code=201)
def create_recurring_payment_route(
    payload: RecurringPaymentCreate,
    month_year: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> RecurringPaymentRead:
    payment = create_recurring_payment(session, payload)
    if month_year:
        ensure_recurring_transactions_for_month(session, month_year)
        payment = get_recurring_payment(session, payment.id)
    return RecurringPaymentRead.model_validate(payment)


@router.patch("/{payment_id}", response_model=RecurringPaymentRead)
def patch_recurring_payment(
    payment_id: int,
    payload: RecurringPaymentUpdate,
    session: Session = Depends(get_session),
) -> RecurringPaymentRead:
    return RecurringPaymentRead.model_validate(update_recurring_payment(session, payment_id, payload))


@router.delete("/{payment_id}", status_code=204)
def remove_recurring_payment(
    payment_id: int,
    session: Session = Depends(get_session),
) -> None:
    delete_recurring_payment(session, payment_id)
