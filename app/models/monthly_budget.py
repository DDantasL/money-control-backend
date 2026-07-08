from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.user import User


class MonthlyBudget(SQLModel, table=True):
    __tablename__ = "monthly_budgets"
    __table_args__ = (UniqueConstraint("user_id", "month_year", name="uq_user_month"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    month_year: str = Field(max_length=7, index=True, description="Formato YYYY-MM")
    expected_contribution: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    actual_contribution: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="monthly_budgets")
