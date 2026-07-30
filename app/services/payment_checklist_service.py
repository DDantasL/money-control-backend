from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import PaymentCard, Transaction, User
from app.models.payment_checklist import PaymentChecklistItem
from app.schemas.payment_checklist import PaymentChecklistStatus, PaymentChecklistUpsert


def get_checklist_status(session: Session, month_year: str) -> PaymentChecklistStatus:
    items = list(
        session.exec(
            select(PaymentChecklistItem).where(
                PaymentChecklistItem.month_year == month_year,
                PaymentChecklistItem.checked == True,  # noqa: E712
            )
        ).all()
    )
    paid_card_ids = sorted({item.card_id for item in items if item.card_id is not None})
    paid_transaction_ids = sorted(
        {item.transaction_id for item in items if item.transaction_id is not None}
    )
    return PaymentChecklistStatus(
        paid_card_ids=paid_card_ids,
        paid_transaction_ids=paid_transaction_ids,
    )


def upsert_checklist_item(session: Session, payload: PaymentChecklistUpsert) -> PaymentChecklistItem:
    if payload.card_id is not None:
        card = session.get(PaymentCard, payload.card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Cartão não encontrado")
        owner = session.get(User, card.user_id)
        if owner and owner.is_family:
            raise HTTPException(
                status_code=400,
                detail="No Caixa da Família, marque cada lançamento individualmente.",
            )

        existing = session.exec(
            select(PaymentChecklistItem).where(
                PaymentChecklistItem.month_year == payload.month_year,
                PaymentChecklistItem.card_id == payload.card_id,
            )
        ).first()
    else:
        transaction = session.get(Transaction, payload.transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transação não encontrada")

        existing = session.exec(
            select(PaymentChecklistItem).where(
                PaymentChecklistItem.transaction_id == payload.transaction_id
            )
        ).first()

    if not payload.checked:
        if existing:
            session.delete(existing)
            session.commit()
            return PaymentChecklistItem(
                id=existing.id,
                month_year=payload.month_year,
                card_id=payload.card_id,
                transaction_id=payload.transaction_id,
                checked=False,
                updated_at=datetime.utcnow(),
            )
        return PaymentChecklistItem(
            month_year=payload.month_year,
            card_id=payload.card_id,
            transaction_id=payload.transaction_id,
            checked=False,
            updated_at=datetime.utcnow(),
        )

    if existing:
        existing.checked = True
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    item = PaymentChecklistItem(
        month_year=payload.month_year,
        card_id=payload.card_id,
        transaction_id=payload.transaction_id,
        checked=True,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def delete_checklist_for_transactions(session: Session, transaction_ids: list[int]) -> None:
    if not transaction_ids:
        return
    items = session.exec(
        select(PaymentChecklistItem).where(
            PaymentChecklistItem.transaction_id.in_(transaction_ids)
        )
    ).all()
    for item in items:
        session.delete(item)


def delete_checklist_for_card(session: Session, card_id: int) -> None:
    items = session.exec(
        select(PaymentChecklistItem).where(PaymentChecklistItem.card_id == card_id)
    ).all()
    for item in items:
        session.delete(item)
