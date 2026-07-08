from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import PaymentCard, User
from app.schemas.transaction import PaymentCardCreate, PaymentCardRead, PaymentCardUpdate
from app.services.delete_service import delete_card
from app.services.update_service import update_card

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=list[PaymentCardRead])
def list_cards(
    user_id: int | None = Query(default=None),
    active_only: bool = Query(default=True),
    session: Session = Depends(get_session),
) -> list[PaymentCard]:
    statement = select(PaymentCard).order_by(PaymentCard.user_id, PaymentCard.name)
    if user_id is not None:
        statement = statement.where(PaymentCard.user_id == user_id)
    if active_only:
        statement = statement.where(PaymentCard.active.is_(True))
    return list(session.exec(statement).all())


@router.post("", response_model=PaymentCardRead, status_code=201)
def create_card(
    payload: PaymentCardCreate,
    session: Session = Depends(get_session),
) -> PaymentCard:
    owner = session.get(User, payload.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if owner.is_family:
        raise HTTPException(
            status_code=400,
            detail="O cartão da Família é criado automaticamente pelo sistema.",
        )

    card = PaymentCard.model_validate(payload)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.patch("/{card_id}", response_model=PaymentCardRead)
def patch_card(
    card_id: int,
    payload: PaymentCardUpdate,
    session: Session = Depends(get_session),
) -> PaymentCard:
    return update_card(session, card_id, payload)


@router.delete("/{card_id}", status_code=204)
def remove_card(card_id: int, session: Session = Depends(get_session)) -> None:
    delete_card(session, card_id)
