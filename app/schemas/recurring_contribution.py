from decimal import Decimal

from pydantic import BaseModel, Field


class RecurringContributionCreate(BaseModel):
    user_id: int
    expected_contribution: Decimal = Field(ge=0, decimal_places=2)


class RecurringContributionUpdate(BaseModel):
    expected_contribution: Decimal = Field(ge=0, decimal_places=2)
    active: bool = True


class RecurringContributionRead(BaseModel):
    id: int
    user_id: int
    expected_contribution: Decimal
    active: bool

    model_config = {"from_attributes": True}
