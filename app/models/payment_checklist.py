from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class PaymentChecklistItem(SQLModel, table=True):
    """Marca fatura de cartão paga (por mês) ou item do Caixa pago."""

    __tablename__ = "payment_checklist_items"
    __table_args__ = (
        UniqueConstraint("month_year", "card_id", name="uq_checklist_card_month"),
        UniqueConstraint("transaction_id", name="uq_checklist_transaction"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    month_year: str = Field(max_length=7, index=True, description="Formato YYYY-MM")
    card_id: Optional[int] = Field(default=None, foreign_key="payment_cards.id", index=True)
    transaction_id: Optional[int] = Field(default=None, foreign_key="transactions.id", index=True)
    checked: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
