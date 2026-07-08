from decimal import Decimal

from pydantic import BaseModel, Field


class RecurringPaymentCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    total_value: Decimal = Field(gt=0, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    card_id: int
    day_of_month: int = Field(default=1, ge=1, le=28)


class RecurringPaymentUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    total_value: Decimal = Field(gt=0, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    card_id: int
    day_of_month: int = Field(ge=1, le=28)
    active: bool = True


class RecurringPaymentRead(BaseModel):
    id: int
    description: str
    total_value: Decimal
    category: str
    card_id: int
    day_of_month: int
    active: bool

    model_config = {"from_attributes": True}
