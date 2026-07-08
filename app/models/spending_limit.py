from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.user import User


class SpendingLimit(SQLModel, table=True):
    """Teto de gastos mensal global ou por categoria."""

    __tablename__ = "spending_limits"
    __table_args__ = (
        UniqueConstraint("month_year", "category", name="uq_limit_month_category"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    month_year: str = Field(max_length=7, index=True, description="Formato YYYY-MM")
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Null = limite global do mês",
    )
    limit_value: Decimal = Field(max_digits=12, decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="spending_limits")
