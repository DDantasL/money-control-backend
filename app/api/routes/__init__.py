from fastapi import APIRouter, Depends

from app.api.deps import get_current_account
from app.api.routes import (
    auth,
    budgets,
    cards,
    dashboard,
    payment_checklist,
    recurring_contributions,
    recurring_payments,
    spending_limits,
    transactions,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)

protected_router = APIRouter(dependencies=[Depends(get_current_account)])
protected_router.include_router(users.router)
protected_router.include_router(cards.router)
protected_router.include_router(transactions.router)
protected_router.include_router(budgets.router)
protected_router.include_router(spending_limits.router)
protected_router.include_router(recurring_payments.router)
protected_router.include_router(recurring_contributions.router)
protected_router.include_router(payment_checklist.router)
protected_router.include_router(dashboard.router)

api_router.include_router(protected_router)
