from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.payment_card import PaymentCard


class RecurringPayment(SQLModel, table=True):
    __tablename__ = "recurring_payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(max_length=255)
    total_value: Decimal = Field(max_digits=12, decimal_places=2)
    category: str = Field(max_length=100, index=True)
    card_id: int = Field(foreign_key="payment_cards.id", index=True)
    day_of_month: int = Field(default=1, ge=1, le=28)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    card: "PaymentCard" = Relationship()
