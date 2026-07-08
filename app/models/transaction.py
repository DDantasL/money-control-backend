from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.payment_card import PaymentCard
    from app.models.transaction_split import TransactionSplit


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(max_length=255)
    total_value: Decimal = Field(max_digits=12, decimal_places=2)
    category: str = Field(max_length=100, index=True)
    transaction_date: date = Field(index=True)
    total_installments: int = Field(default=1, ge=1)
    current_installment: int = Field(default=1, ge=1)
    card_id: int = Field(foreign_key="payment_cards.id", index=True)
    parent_transaction_id: Optional[int] = Field(default=None, foreign_key="transactions.id")
    recurring_payment_id: Optional[int] = Field(default=None, foreign_key="recurring_payments.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    card: "PaymentCard" = Relationship(back_populates="transactions")
    splits: list["TransactionSplit"] = Relationship(back_populates="transaction")

    @property
    def installment_value(self) -> Decimal:
        return (self.total_value / self.total_installments).quantize(Decimal("0.01"))
