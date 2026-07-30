from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class ContributionExtra(SQLModel, table=True):
    """Valor avulso somado à contribuição base do mês."""

    __tablename__ = "contribution_extras"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    month_year: str = Field(max_length=7, index=True, description="Formato YYYY-MM")
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.utcnow)
