from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.user import User


class RecurringContribution(SQLModel, table=True):
    __tablename__ = "recurring_contributions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_recurring_contribution_user"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    expected_contribution: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship()
