from decimal import Decimal

from sqlmodel import Session, select

from app.models import PaymentCard, User
from app.schemas.transaction import TransactionSplitCreate

FAMILY_USER_NAME = "Família"
FAMILY_CARD_NAME = "Caixa"


def ensure_family_account(session: Session) -> User:
    """Garante o pagador coletivo Família e seu cartão Caixa."""
    family = session.exec(select(User).where(User.is_family.is_(True))).first()

    if not family:
        family = User(name=FAMILY_USER_NAME, is_family=True)
        session.add(family)
        session.flush()

    family_card = session.exec(
        select(PaymentCard).where(PaymentCard.user_id == family.id)
    ).first()
    if not family_card:
        session.add(PaymentCard(user_id=family.id, name=FAMILY_CARD_NAME))
        session.flush()

    session.commit()
    session.refresh(family)
    return family


def get_family_user(session: Session) -> User | None:
    return session.exec(select(User).where(User.is_family.is_(True))).first()


def is_family_card(session: Session, card_id: int) -> bool:
    card = session.get(PaymentCard, card_id)
    if not card:
        return False
    owner = session.get(User, card.user_id)
    return bool(owner and owner.is_family)


def resolve_payment_splits(
    session: Session,
    card_id: int,
    total_value: Decimal,
    splits: list[TransactionSplitCreate],
) -> list[TransactionSplitCreate]:
    """Despesas pagas pela Família debitam do caixa coletivo — um único pagador."""
    card = session.get(PaymentCard, card_id)
    if not card:
        return splits
    owner = session.get(User, card.user_id)
    if owner and owner.is_family:
        return [TransactionSplitCreate(user_id=owner.id, split_value=total_value)]
    return splits
