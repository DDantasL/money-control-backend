from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.payment_checklist import PaymentChecklistStatus


class LimitAlertLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


class CategorySpending(BaseModel):
    category: str
    total: Decimal
    percentage: float


class CardSpending(BaseModel):
    card_id: int
    card_name: str
    user_id: int
    user_name: str
    total: Decimal
    percentage: float
    transaction_count: int


class TransactionSplitDetail(BaseModel):
    user_id: int
    user_name: str
    split_value: Decimal


class TransactionDetail(BaseModel):
    id: int
    description: str
    category: str
    transaction_date: date
    total_value: Decimal
    installment_amount: Decimal
    total_installments: int
    current_installment: int
    card_id: int
    card_name: str
    paid_by_user_id: int
    paid_by_user_name: str
    paid_from_family_pool: bool
    splits: list[TransactionSplitDetail]


class LimitProgress(BaseModel):
    category: str | None
    limit_value: Decimal
    spent: Decimal
    percentage: float
    alert_level: LimitAlertLevel


class MemberBalance(BaseModel):
    user_id: int
    user_name: str
    actual_contribution: Decimal
    card_spent_for_others: Decimal
    individual_expenses: Decimal
    balance: Decimal


class TransferSuggestion(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: Decimal


class MonthlyDashboard(BaseModel):
    month_year: str
    total_spent: Decimal
    total_contributions: Decimal
    family_pool_spent: Decimal
    family_pool_balance: Decimal
    personal_card_spent: Decimal
    spending_by_category: list[CategorySpending]
    spending_by_card: list[CardSpending]
    transaction_details: list[TransactionDetail]
    limit_progress: list[LimitProgress]
    member_balances: list[MemberBalance]
    transfer_suggestions: list[TransferSuggestion]
    payment_checklist: PaymentChecklistStatus
