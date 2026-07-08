from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UserUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    id: int
    name: str
    is_family: bool = False

    model_config = {"from_attributes": True}


class PaymentCardCreate(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=100)
    nickname: str | None = Field(default=None, max_length=100)


class PaymentCardUpdate(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=100)
    nickname: str | None = Field(default=None, max_length=100)


class PaymentCardRead(BaseModel):
    id: int
    user_id: int
    name: str
    nickname: str | None = None
    active: bool = True

    model_config = {"from_attributes": True}


class MonthlyBudgetCreate(BaseModel):
    user_id: int
    month_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    actual_contribution: Decimal = Field(ge=0, decimal_places=2)


class MonthlyBudgetRead(BaseModel):
    id: int
    user_id: int
    month_year: str
    expected_contribution: Decimal
    actual_contribution: Decimal

    model_config = {"from_attributes": True}


class TransactionSplitCreate(BaseModel):
    user_id: int
    split_value: Decimal = Field(gt=0, decimal_places=2)


class TransactionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    total_value: Decimal = Field(gt=0, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    transaction_date: date
    total_installments: int = Field(default=1, ge=1, le=48)
    card_id: int
    splits: list[TransactionSplitCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_splits_sum(self) -> "TransactionCreate":
        total = sum(split.split_value for split in self.splits)
        if total != self.total_value:
            raise ValueError(
                f"A soma dos splits ({total}) deve ser igual ao valor total ({self.total_value})"
            )
        return self


class TransactionRead(BaseModel):
    id: int
    description: str
    total_value: Decimal
    category: str
    transaction_date: date
    total_installments: int
    current_installment: int
    card_id: int
    parent_transaction_id: int | None = None
    recurring_payment_id: int | None = None

    model_config = {"from_attributes": True}


class TransactionSplitRead(BaseModel):
    user_id: int
    split_value: Decimal

    model_config = {"from_attributes": True}


class TransactionDetailRead(TransactionRead):
    splits: list[TransactionSplitRead]


class TransactionUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    total_value: Decimal = Field(gt=0, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    transaction_date: date
    card_id: int
    splits: list[TransactionSplitCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_splits_sum(self) -> "TransactionUpdate":
        total = sum(split.split_value for split in self.splits)
        if total != self.total_value:
            raise ValueError(
                f"A soma dos splits ({total}) deve ser igual ao valor total ({self.total_value})"
            )
        return self


class SpendingLimitCreate(BaseModel):
    month_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    category: str | None = None
    user_id: int | None = None
    limit_value: Decimal = Field(gt=0, decimal_places=2)


class SpendingLimitUpdate(BaseModel):
    limit_value: Decimal = Field(gt=0, decimal_places=2)


class SpendingLimitRead(BaseModel):
    id: int
    month_year: str
    category: str | None
    user_id: int | None
    limit_value: Decimal

    model_config = {"from_attributes": True}
