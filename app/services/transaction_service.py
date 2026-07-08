from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from app.models import Transaction, TransactionSplit
from app.schemas.transaction import TransactionCreate, TransactionSplitCreate
from app.services.recurring_payment_service import ensure_recurring_transactions_for_month
from app.services.split_utils import quantize


def _quantize(value: Decimal) -> Decimal:
    return quantize(value)


def _add_months(source_date: date, months: int) -> date:
    target = source_date + relativedelta(months=months)
    last_day = monthrange(target.year, target.month)[1]
    return target.replace(day=min(source_date.day, last_day))



def create_transaction_with_installments(
    session: Session,
    payload: TransactionCreate,
) -> list[Transaction]:
    """Cria a transação principal e parcelas futuras com splits proporcionais."""
    installment_value = _quantize(payload.total_value / payload.total_installments)
    created: list[Transaction] = []

    parent: Transaction | None = None
    for installment_number in range(1, payload.total_installments + 1):
        installment_date = _add_months(payload.transaction_date, installment_number - 1)
        transaction = Transaction(
            description=payload.description,
            total_value=payload.total_value,
            category=payload.category,
            transaction_date=installment_date,
            total_installments=payload.total_installments,
            current_installment=installment_number,
            card_id=payload.card_id,
            parent_transaction_id=parent.id if parent else None,
        )
        session.add(transaction)
        session.flush()

        if parent is None:
            parent = transaction

        split_ratio = installment_value / payload.total_value
        for split in payload.splits:
            split_amount = _quantize(split.split_value * split_ratio)
            session.add(
                TransactionSplit(
                    transaction_id=transaction.id,
                    user_id=split.user_id,
                    split_value=split_amount,
                )
            )

        created.append(transaction)

    session.commit()
    for transaction in created:
        session.refresh(transaction)
    return created


def get_transactions_for_month(session: Session, month_year: str) -> list[Transaction]:
    ensure_recurring_transactions_for_month(session, month_year)

    year, month = map(int, month_year.split("-"))
    start = date(year, month, 1)
    end = _add_months(start, 1) - relativedelta(days=1)

    statement = (
        select(Transaction)
        .where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)
        .order_by(Transaction.transaction_date)
    )
    return list(session.exec(statement).all())
