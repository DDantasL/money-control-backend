from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import PaymentCard, RecurringPayment, RecurringPaymentSkip, SpendingLimit, Transaction, TransactionSplit, User
from app.schemas.transaction import (
    PaymentCardUpdate,
    SpendingLimitUpdate,
    TransactionUpdate,
    UserUpdate,
)
from app.services.delete_service import _get_series_transactions, _month_year_from_date
from app.services.family_service import resolve_payment_splits
from app.services.family_service import FAMILY_USER_NAME


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _replace_splits(
    session: Session,
    transaction_id: int,
    full_splits: list,
    installment_ratio: Decimal,
) -> None:
    existing = session.exec(
        select(TransactionSplit).where(TransactionSplit.transaction_id == transaction_id)
    ).all()
    for split in existing:
        session.delete(split)

    for split in full_splits:
        session.add(
            TransactionSplit(
                transaction_id=transaction_id,
                user_id=split.user_id,
                split_value=_quantize(split.split_value * installment_ratio),
            )
        )


def update_user(session: Session, user_id: int, payload: UserUpdate) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if user.is_family:
        raise HTTPException(status_code=400, detail="O pagador Família não pode ser editado.")
    if payload.name.strip().lower() == FAMILY_USER_NAME.lower():
        raise HTTPException(status_code=400, detail="Este nome é reservado para o pagador Família.")

    user.name = payload.name.strip()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_card(session: Session, card_id: int, payload: PaymentCardUpdate) -> PaymentCard:
    card = session.get(PaymentCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    owner = session.get(User, card.user_id)
    if owner and owner.is_family:
        raise HTTPException(status_code=400, detail="O cartão da Família não pode ser editado.")

    new_owner = session.get(User, payload.user_id)
    if not new_owner:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if new_owner.is_family:
        raise HTTPException(status_code=400, detail="O cartão da Família pertence ao pagador coletivo.")

    card.user_id = payload.user_id
    card.name = payload.name.strip()
    card.nickname = payload.nickname.strip() if payload.nickname else None
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def update_spending_limit(
    session: Session,
    limit_id: int,
    payload: SpendingLimitUpdate,
) -> SpendingLimit:
    limit = session.get(SpendingLimit, limit_id)
    if not limit:
        raise HTTPException(status_code=404, detail="Limite não encontrado")

    limit.limit_value = payload.limit_value
    session.add(limit)
    session.commit()
    session.refresh(limit)
    return limit


def get_transaction_detail(session: Session, transaction_id: int) -> tuple[Transaction, list[TransactionSplit]]:
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    splits = list(
        session.exec(
            select(TransactionSplit).where(TransactionSplit.transaction_id == transaction_id)
        ).all()
    )
    return transaction, splits


def _apply_transaction_update(
    session: Session,
    transaction: Transaction,
    payload: TransactionUpdate,
    resolved_splits: list,
    *,
    installments_scope: Literal["single", "future", "all"] = "single",
) -> None:
    installment_ratio = Decimal("1") / Decimal(transaction.total_installments)
    if transaction.total_installments <= 1:
        target_transactions = [transaction]
    else:
        series = _get_series_transactions(session, transaction)
        if installments_scope == "all":
            target_transactions = series
        elif installments_scope == "future":
            # Mantém a parcela selecionada e todas as futuras (>= current_installment).
            target_transactions = [
                tx for tx in series if tx.current_installment >= transaction.current_installment
            ]
        elif installments_scope == "single":
            target_transactions = [transaction]
        else:
            raise HTTPException(status_code=400, detail="Escopo de parcelas inválido")

    for item in target_transactions:
        item.description = payload.description.strip()
        item.category = payload.category.strip()
        item.card_id = payload.card_id
        item.total_value = payload.total_value

        # Somente a parcela selecionada deve ter a data alterada.
        if item.id == transaction.id:
            item.transaction_date = payload.transaction_date

        session.add(item)
        _replace_splits(session, item.id, resolved_splits, installment_ratio)


def _update_recurring_transaction(
    session: Session,
    transaction: Transaction,
    payload: TransactionUpdate,
    resolved_splits: list,
    scope: Literal["single", "future"],
) -> Transaction:
    payment = session.get(RecurringPayment, transaction.recurring_payment_id)
    if not payment:
        _apply_transaction_update(session, transaction, payload, resolved_splits)
        session.commit()
        session.refresh(transaction)
        return transaction

    installment_ratio = Decimal("1")

    if scope == "single":
        _apply_transaction_update(session, transaction, payload, resolved_splits)
        transaction.recurring_payment_id = None
        session.add(transaction)

        month_year = _month_year_from_date(transaction.transaction_date)
        existing_skip = session.exec(
            select(RecurringPaymentSkip).where(
                RecurringPaymentSkip.recurring_payment_id == payment.id,
                RecurringPaymentSkip.month_year == month_year,
            )
        ).first()
        if not existing_skip:
            session.add(
                RecurringPaymentSkip(
                    recurring_payment_id=payment.id,
                    month_year=month_year,
                )
            )

        session.commit()
        session.refresh(transaction)
        return transaction

    day_of_month = min(payload.transaction_date.day, 28)
    payment.description = payload.description.strip()
    payment.total_value = payload.total_value
    payment.category = payload.category.strip()
    payment.card_id = payload.card_id
    payment.day_of_month = day_of_month
    session.add(payment)

    future_transactions = list(
        session.exec(
            select(Transaction).where(
                Transaction.recurring_payment_id == payment.id,
                Transaction.transaction_date >= transaction.transaction_date,
            )
        ).all()
    )

    for item in future_transactions:
        item.description = payment.description
        item.category = payment.category
        item.card_id = payment.card_id
        item.total_value = payment.total_value
        if item.id == transaction.id:
            item.transaction_date = payload.transaction_date
        session.add(item)
        if item.id is not None:
            _replace_splits(session, item.id, resolved_splits, installment_ratio)

    session.commit()
    session.refresh(transaction)
    return transaction


def update_transaction(
    session: Session,
    transaction_id: int,
    payload: TransactionUpdate,
    *,
    installments_scope: Literal["single", "future", "all"] = "single",
    recurring_scope: Literal["single", "future"] | None = None,
) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    card = session.get(PaymentCard, payload.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    resolved_splits = resolve_payment_splits(
        session, payload.card_id, payload.total_value, payload.splits
    )

    if transaction.recurring_payment_id and recurring_scope:
        return _update_recurring_transaction(
            session, transaction, payload, resolved_splits, recurring_scope
        )

    _apply_transaction_update(
        session,
        transaction,
        payload,
        resolved_splits,
        installments_scope=installments_scope,
    )
    session.commit()
    session.refresh(transaction)
    return transaction
