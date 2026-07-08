from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.monthly_budget import MonthlyBudget
    from app.models.payment_card import PaymentCard
    from app.models.spending_limit import SpendingLimit
    from app.models.transaction_split import TransactionSplit


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    is_family: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    monthly_budgets: list["MonthlyBudget"] = Relationship(back_populates="user")
    payment_cards: list["PaymentCard"] = Relationship(back_populates="owner")
    transaction_splits: list["TransactionSplit"] = Relationship(back_populates="user")
    spending_limits: list["SpendingLimit"] = Relationship(back_populates="user")
