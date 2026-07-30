from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    MonthlyBudget,
    PaymentCard,
    RecurringContribution,
    RecurringPayment,
    RecurringPaymentSkip,
    SpendingLimit,
    Transaction,
    TransactionSplit,
    User,
)
from app.services.payment_checklist_service import (
    delete_checklist_for_card,
    delete_checklist_for_transactions,
)


def _delete_transaction_splits(session: Session, transaction_ids: list[int]) -> None:
    if not transaction_ids:
        return
    splits = session.exec(
        select(TransactionSplit).where(TransactionSplit.transaction_id.in_(transaction_ids))
    ).all()
    for split in splits:
        session.delete(split)


def _delete_transactions(session: Session, transactions: list[Transaction]) -> None:
    if not transactions:
        return

    transaction_ids = [tx.id for tx in transactions if tx.id is not None]
    delete_checklist_for_transactions(session, transaction_ids)
    _delete_transaction_splits(session, transaction_ids)

    children = [tx for tx in transactions if tx.parent_transaction_id is not None]
    parents = [tx for tx in transactions if tx.parent_transaction_id is None]

    for transaction in children:
        session.delete(transaction)
    # Garante que as exclusões das "filhas" ocorram no banco antes de remover os "pais"
    # (evita ForeignKeyViolation por parent_transaction_id).
    session.flush()
    for transaction in parents:
        session.delete(transaction)


def _get_series_transactions(session: Session, transaction: Transaction) -> list[Transaction]:
    root_id = transaction.parent_transaction_id or transaction.id
    root = session.get(Transaction, root_id)
    if not root:
        return [transaction]

    children = list(
        session.exec(select(Transaction).where(Transaction.parent_transaction_id == root.id)).all()
    )
    return [root, *children]


def _month_year_from_date(value: date) -> str:
    return value.strftime("%Y-%m")


def _delete_recurring_transaction(
    session: Session,
    transaction: Transaction,
    scope: Literal["single", "future", "all"],
) -> None:
    payment_id = transaction.recurring_payment_id
    if not payment_id:
        raise HTTPException(status_code=400, detail="Transação não é um pagamento fixo")

    if scope == "single":
        month_year = _month_year_from_date(transaction.transaction_date)
        _delete_transactions(session, [transaction])
        existing_skip = session.exec(
            select(RecurringPaymentSkip).where(
                RecurringPaymentSkip.recurring_payment_id == payment_id,
                RecurringPaymentSkip.month_year == month_year,
            )
        ).first()
        if not existing_skip:
            session.add(
                RecurringPaymentSkip(
                    recurring_payment_id=payment_id,
                    month_year=month_year,
                )
            )
        session.commit()
        return

    if scope == "future":
        targets = list(
            session.exec(
                select(Transaction).where(
                    Transaction.recurring_payment_id == payment_id,
                    Transaction.transaction_date >= transaction.transaction_date,
                )
            ).all()
        )
        _delete_transactions(session, targets)
        payment = session.get(RecurringPayment, payment_id)
        if payment:
            payment.active = False
            session.add(payment)
        session.commit()
        return

    if scope == "all":
        targets = list(
            session.exec(
                select(Transaction).where(Transaction.recurring_payment_id == payment_id)
            ).all()
        )
        _delete_transactions(session, targets)
        skips = list(
            session.exec(
                select(RecurringPaymentSkip).where(
                    RecurringPaymentSkip.recurring_payment_id == payment_id
                )
            ).all()
        )
        for skip in skips:
            session.delete(skip)
        payment = session.get(RecurringPayment, payment_id)
        if payment:
            session.delete(payment)
        session.commit()
        return

    raise HTTPException(status_code=400, detail="Escopo de exclusão inválido")


def delete_transaction(
    session: Session,
    transaction_id: int,
    *,
    all_installments: bool = False,
    recurring_scope: Literal["single", "future", "all"] | None = None,
) -> None:
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    if transaction.recurring_payment_id and recurring_scope:
        _delete_recurring_transaction(session, transaction, recurring_scope)
        return

    if all_installments and transaction.total_installments > 1:
        targets = _get_series_transactions(session, transaction)
    else:
        children = list(
            session.exec(
                select(Transaction).where(Transaction.parent_transaction_id == transaction.id)
            ).all()
        )
        for child in children:
            child.parent_transaction_id = transaction.parent_transaction_id
            session.add(child)
        targets = [transaction]

    _delete_transactions(session, targets)
    session.commit()


def delete_card_transactions(session: Session, card_id: int) -> None:
    transactions = list(session.exec(select(Transaction).where(Transaction.card_id == card_id)).all())
    _delete_transactions(session, transactions)


def delete_card(session: Session, card_id: int) -> None:
    card = session.get(PaymentCard, card_id)
    if not card or not card.active:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    owner = session.get(User, card.user_id)
    if owner and owner.is_family:
        raise HTTPException(status_code=400, detail="O cartão da Família não pode ser excluído.")

    recurring_payments = list(
        session.exec(
            select(RecurringPayment).where(
                RecurringPayment.card_id == card_id,
                RecurringPayment.active.is_(True),
            )
        ).all()
    )
    for payment in recurring_payments:
        payment.active = False
        session.add(payment)

    card.active = False
    session.add(card)
    session.commit()


def delete_user(session: Session, user_id: int) -> None:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if user.is_family:
        raise HTTPException(status_code=400, detail="O pagador Família não pode ser excluído.")

    cards = list(session.exec(select(PaymentCard).where(PaymentCard.user_id == user_id)).all())
    card_ids = {card.id for card in cards if card.id is not None}

    splits = list(
        session.exec(select(TransactionSplit).where(TransactionSplit.user_id == user_id)).all()
    )
    for split in splits:
        transaction = session.get(Transaction, split.transaction_id)
        if transaction and transaction.card_id not in card_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Este membro participa de transações pagas por outros. "
                    "Exclua essas transações antes de remover o membro."
                ),
            )

    for card in cards:
        if card.id is not None:
            delete_checklist_for_card(session, card.id)
            delete_card_transactions(session, card.id)
        session.delete(card)

    budgets = list(
        session.exec(select(MonthlyBudget).where(MonthlyBudget.user_id == user_id)).all()
    )
    for budget in budgets:
        session.delete(budget)

    recurring_contributions = list(
        session.exec(
            select(RecurringContribution).where(RecurringContribution.user_id == user_id)
        ).all()
    )
    for contribution in recurring_contributions:
        session.delete(contribution)

    limits = list(
        session.exec(select(SpendingLimit).where(SpendingLimit.user_id == user_id)).all()
    )
    for limit in limits:
        session.delete(limit)

    session.delete(user)
    session.commit()


def delete_budget(session: Session, budget_id: int) -> None:
    budget = session.get(MonthlyBudget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Contribuição não encontrada")

    session.delete(budget)
    session.commit()


def delete_spending_limit(session: Session, limit_id: int) -> None:
    limit = session.get(SpendingLimit, limit_id)
    if not limit:
        raise HTTPException(status_code=404, detail="Limite não encontrado")

    session.delete(limit)
    session.commit()
