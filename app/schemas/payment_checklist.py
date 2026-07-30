from pydantic import BaseModel, Field, model_validator


class PaymentChecklistUpsert(BaseModel):
    month_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    card_id: int | None = None
    transaction_id: int | None = None
    checked: bool = True

    @model_validator(mode="after")
    def exactly_one_target(self) -> "PaymentChecklistUpsert":
        has_card = self.card_id is not None
        has_tx = self.transaction_id is not None
        if has_card == has_tx:
            raise ValueError("Informe exatamente um de: card_id ou transaction_id")
        return self


class PaymentChecklistRead(BaseModel):
    id: int
    month_year: str
    card_id: int | None
    transaction_id: int | None
    checked: bool


class PaymentChecklistStatus(BaseModel):
    paid_card_ids: list[int]
    paid_transaction_ids: list[int]
