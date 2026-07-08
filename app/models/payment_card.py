from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class PaymentCard(SQLModel, table=True):
    __tablename__ = "payment_cards"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    nickname: Optional[str] = Field(default=None, max_length=100)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    owner: "User" = Relationship(back_populates="payment_cards")
    transactions: list["Transaction"] = Relationship(back_populates="card")

    @property
    def display_name(self) -> str:
        if self.nickname:
            return f"{self.name} — {self.nickname}"
        return self.name
