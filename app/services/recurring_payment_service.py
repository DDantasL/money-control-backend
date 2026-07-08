from calendar import monthrange
from datetime import date

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import PaymentCard, RecurringPayment, RecurringPaymentSkip, Transaction, TransactionSplit, User
from app.schemas.recurring_payment import RecurringPaymentCreate, RecurringPaymentUpdate
from app.schemas.transaction import TransactionSplitCreate
from app.services.family_service import resolve_payment_splits
from app.services.split_utils import split_evenly


def _month_bounds(month_year: str) -> tuple[date, date]:
    year, month = map(int, month_year.split("-"))
    start = date(year, month, 1)
    end = start + relativedelta(months=1) - relativedelta(days=1)
    return start, end


def _transaction_splits_for_payment(
    session: Session,
    payment: RecurringPayment,
) -> list[TransactionSplitCreate]:
    """Calcula splits na geração: Família = pagador único; cartão pessoal = divide entre membros."""
    member_ids = [
        user.id
        for user in session.exec(select(User).where(User.is_family.is_(False))).all()
        if user.id is not None
    ]
    base_splits = split_evenly(payment.total_value, member_ids) if member_ids else []
    return resolve_payment_splits(session, payment.card_id, payment.total_value, base_splits)


def list_recurring_payments(session: Session) -> list[RecurringPayment]:
    return list(
        session.exec(
            select(RecurringPayment).order_by(RecurringPayment.description)
        ).all()
    )


def get_recurring_payment(session: Session, payment_id: int) -> RecurringPayment:
    payment = session.get(RecurringPayment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento fixo não encontrado")
    return payment


def create_recurring_payment(
    session: Session,
    payload: RecurringPaymentCreate,
) -> RecurringPayment:
    card = session.get(PaymentCard, payload.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    payment = RecurringPayment(
        description=payload.description.strip(),
        total_value=payload.total_value,
        category=payload.category.strip(),
        card_id=payload.card_id,
        day_of_month=payload.day_of_month,
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


def update_recurring_payment(
    session: Session,
    payment_id: int,
    payload: RecurringPaymentUpdate,
) -> RecurringPayment:
    payment = get_recurring_payment(session, payment_id)

    card = session.get(PaymentCard, payload.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    payment.description = payload.description.strip()
    payment.total_value = payload.total_value
    payment.category = payload.category.strip()
    payment.card_id = payload.card_id
    payment.day_of_month = payload.day_of_month
    payment.active = payload.active
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


def delete_recurring_payment(session: Session, payment_id: int) -> None:
    payment = session.get(RecurringPayment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento fixo não encontrado")

    session.delete(payment)
    session.commit()


def _create_transaction_for_month(
    session: Session,
    payment: RecurringPayment,
    month_year: str,
) -> Transaction:
    year, month = map(int, month_year.split("-"))
    day = min(payment.day_of_month, monthrange(year, month)[1])
    transaction_date = date(year, month, day)

    transaction = Transaction(
        description=payment.description,
        total_value=payment.total_value,
        category=payment.category,
        transaction_date=transaction_date,
        total_installments=1,
        current_installment=1,
        card_id=payment.card_id,
        recurring_payment_id=payment.id,
    )
    session.add(transaction)
    session.flush()

    for split in _transaction_splits_for_payment(session, payment):
        session.add(
            TransactionSplit(
                transaction_id=transaction.id,
                user_id=split.user_id,
                split_value=split.split_value,
            )
        )

    return transaction


def ensure_recurring_transactions_for_month(session: Session, month_year: str) -> None:
    """Gera transações dos pagamentos fixos ativos que ainda não existem no mês."""
    start, end = _month_bounds(month_year)
    active_payments = list(
        session.exec(select(RecurringPayment).where(RecurringPayment.active.is_(True)))
    )

    created = False
    for payment in active_payments:
        skipped = session.exec(
            select(RecurringPaymentSkip).where(
                RecurringPaymentSkip.recurring_payment_id == payment.id,
                RecurringPaymentSkip.month_year == month_year,
            )
        ).first()
        if skipped:
            continue

        existing = session.exec(
            select(Transaction).where(
                Transaction.recurring_payment_id == payment.id,
                Transaction.transaction_date >= start,
                Transaction.transaction_date <= end,
            )
        ).first()
        if existing:
            continue

        _create_transaction_for_month(session, payment, month_year)
        created = True

    if created:
        session.commit()
