from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.user import User


class TransactionSplit(SQLModel, table=True):
    __tablename__ = "transaction_splits"

    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(foreign_key="transactions.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    split_value: Decimal = Field(max_digits=12, decimal_places=2)

    transaction: "Transaction" = Relationship(back_populates="splits")
    user: "User" = Relationship(back_populates="transaction_splits")
