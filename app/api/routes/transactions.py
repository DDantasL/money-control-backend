from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.database import get_session
from app.models import PaymentCard, Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionDetailRead,
    TransactionRead,
    TransactionSplitRead,
    TransactionUpdate,
)
from app.services.transaction_service import (
    create_transaction_with_installments,
    get_transactions_for_month,
)
from app.services.delete_service import delete_transaction
from app.services.family_service import resolve_payment_splits
from app.services.update_service import get_transaction_detail, update_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    month_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
) -> list[Transaction]:
    return get_transactions_for_month(session, month_year)


@router.post("", response_model=list[TransactionRead], status_code=201)
def create_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
) -> list[Transaction]:
    card = session.get(PaymentCard, payload.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")

    resolved_splits = resolve_payment_splits(
        session, payload.card_id, payload.total_value, payload.splits
    )
    payload = payload.model_copy(update={"splits": resolved_splits})
    return create_transaction_with_installments(session, payload)


@router.get("/{transaction_id}", response_model=TransactionDetailRead)
def get_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
) -> TransactionDetailRead:
    transaction, splits = get_transaction_detail(session, transaction_id)
    return TransactionDetailRead(
        **TransactionRead.model_validate(transaction).model_dump(),
        splits=[TransactionSplitRead.model_validate(split) for split in splits],
    )


@router.patch("/{transaction_id}", response_model=TransactionRead)
def patch_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    all_installments: bool = Query(default=False),
    installments_scope: str | None = Query(default=None, pattern=r"^(single|future|all)$"),
    recurring_scope: str | None = Query(default=None, pattern=r"^(single|future)$"),
    session: Session = Depends(get_session),
) -> Transaction:
    resolved_installments_scope = installments_scope or ("all" if all_installments else "single")
    return update_transaction(
        session,
        transaction_id,
        payload.model_copy(
            update={
                "splits": resolve_payment_splits(
                    session, payload.card_id, payload.total_value, payload.splits
                )
            }
        ),
        installments_scope=resolved_installments_scope,  # type: ignore[arg-type]
        recurring_scope=recurring_scope,  # type: ignore[arg-type]
    )


@router.delete("/{transaction_id}", status_code=204)
def remove_transaction(
    transaction_id: int,
    all_installments: bool = Query(default=False),
    recurring_scope: str | None = Query(default=None, pattern=r"^(single|future|all)$"),
    session: Session = Depends(get_session),
) -> None:
    delete_transaction(
        session,
        transaction_id,
        all_installments=all_installments,
        recurring_scope=recurring_scope,  # type: ignore[arg-type]
    )
