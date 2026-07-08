from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class RecurringPaymentSkip(SQLModel, table=True):
    __tablename__ = "recurring_payment_skips"
    __table_args__ = (
        UniqueConstraint("recurring_payment_id", "month_year", name="uq_recurring_skip_month"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    recurring_payment_id: int = Field(foreign_key="recurring_payments.id", index=True)
    month_year: str = Field(max_length=7, index=True, description="Formato YYYY-MM")
