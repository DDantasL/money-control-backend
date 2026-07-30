from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ContributionExtraCreate(BaseModel):
    user_id: int
    month_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(gt=0, decimal_places=2)


class ContributionExtraRead(BaseModel):
    id: int
    user_id: int
    month_year: str
    amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
