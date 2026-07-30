from decimal import Decimal
from collections import defaultdict

from sqlmodel import Session, select

from app.models import MonthlyBudget, PaymentCard, SpendingLimit, TransactionSplit, User
from app.schemas.dashboard import (
    CardSpending,
    CategorySpending,
    LimitAlertLevel,
    LimitProgress,
    MemberBalance,
    MonthlyDashboard,
    TransactionDetail,
    TransactionSplitDetail,
    TransferSuggestion,
)
from app.services.payment_checklist_service import get_checklist_status
from app.services.recurring_contribution_service import ensure_recurring_contributions_for_month
from app.services.transaction_service import get_transactions_for_month


def _alert_level(spent: Decimal, limit_value: Decimal) -> LimitAlertLevel:
    if limit_value <= 0:
        return LimitAlertLevel.OK
    ratio = float(spent / limit_value)
    if ratio >= 1:
        return LimitAlertLevel.EXCEEDED
    if ratio >= 0.8:
        return LimitAlertLevel.WARNING
    return LimitAlertLevel.OK


def _compute_pairwise_card_transfers(
    transactions: list,
    splits_by_transaction: dict[int, list[TransactionSplit]],
    card_by_id: dict[int, PaymentCard],
    family_user_ids: set[int],
    user_name_by_id: dict[int, str],
) -> list[TransferSuggestion]:
    """Dívidas diretas de cartão pessoal: quem consumiu no cartão de outro deve a ele."""
    owes: dict[tuple[int, int], Decimal] = defaultdict(Decimal)

    for transaction in transactions:
        card = card_by_id.get(transaction.card_id)
        if not card:
            continue
        owner_id = card.user_id
        if owner_id in family_user_ids:
            continue

        tx_splits = splits_by_transaction.get(transaction.id or 0, [])
        for split in tx_splits:
            if split.user_id in family_user_ids or split.user_id == owner_id:
                continue
            owes[(split.user_id, owner_id)] += split.split_value

    suggestions: list[TransferSuggestion] = []
    for (debtor_id, creditor_id), amount in sorted(
        owes.items(), key=lambda item: item[1], reverse=True
    ):
        if amount <= Decimal("0.00"):
            continue
        suggestions.append(
            TransferSuggestion(
                from_user_id=debtor_id,
                from_user_name=user_name_by_id.get(debtor_id, f"Usuário {debtor_id}"),
                to_user_id=creditor_id,
                to_user_name=user_name_by_id.get(creditor_id, f"Usuário {creditor_id}"),
                amount=amount.quantize(Decimal("0.01")),
            )
        )
    return suggestions


def build_monthly_dashboard(session: Session, month_year: str) -> MonthlyDashboard:
    ensure_recurring_contributions_for_month(session, month_year)
    users = list(session.exec(select(User)).all())

    transactions = get_transactions_for_month(session, month_year)
    transaction_ids = [t.id for t in transactions if t.id is not None]

    splits: list[TransactionSplit] = []
    if transaction_ids:
        splits = list(
            session.exec(
                select(TransactionSplit).where(TransactionSplit.transaction_id.in_(transaction_ids))
            ).all()
        )

    splits_by_transaction: dict[int, list[TransactionSplit]] = {}
    for split in splits:
        splits_by_transaction.setdefault(split.transaction_id, []).append(split)

    total_spent = Decimal("0.00")
    category_totals: dict[str, Decimal] = {}
    card_totals: dict[int, Decimal] = {}
    card_transaction_counts: dict[int, int] = {}
    transaction_details: list[TransactionDetail] = []

    card_spent_for_others: dict[int, Decimal] = {user.id: Decimal("0.00") for user in users}
    individual_expenses: dict[int, Decimal] = {user.id: Decimal("0.00") for user in users}
    family_pool_spent = Decimal("0.00")

    user_name_by_id = {user.id: user.name for user in users}
    family_user_ids = {user.id for user in users if user.is_family}
    payment_cards = list(session.exec(select(PaymentCard)).all())
    card_by_id = {card.id: card for card in payment_cards if card.id is not None}

    def card_display_name(card: PaymentCard) -> str:
        return card.display_name

    for transaction in transactions:
        installment_value = (transaction.total_value / transaction.total_installments).quantize(
            Decimal("0.01")
        )
        card = card_by_id.get(transaction.card_id)
        owner_id = card.user_id if card else 0
        is_family_payer = owner_id in family_user_ids
        card_label = card_display_name(card) if card else f"Cartão {transaction.card_id}"

        total_spent += installment_value
        category_totals[transaction.category] = (
            category_totals.get(transaction.category, Decimal("0.00")) + installment_value
        )
        card_totals[transaction.card_id] = (
            card_totals.get(transaction.card_id, Decimal("0.00")) + installment_value
        )
        card_transaction_counts[transaction.card_id] = (
            card_transaction_counts.get(transaction.card_id, 0) + 1
        )

        tx_splits = splits_by_transaction.get(transaction.id or 0, [])
        if is_family_payer:
            family_pool_spent += installment_value
        else:
            for split in tx_splits:
                if split.user_id in family_user_ids:
                    family_pool_spent += split.split_value
                    if owner_id not in family_user_ids:
                        card_spent_for_others[owner_id] = (
                            card_spent_for_others.get(owner_id, Decimal("0.00"))
                            + split.split_value
                        )
                    continue
                individual_expenses[split.user_id] = (
                    individual_expenses.get(split.user_id, Decimal("0.00")) + split.split_value
                )
                if split.user_id != owner_id:
                    card_spent_for_others[owner_id] = (
                        card_spent_for_others.get(owner_id, Decimal("0.00")) + split.split_value
                    )

        transaction_details.append(
            TransactionDetail(
                id=transaction.id or 0,
                description=transaction.description,
                category=transaction.category,
                transaction_date=transaction.transaction_date,
                total_value=transaction.total_value,
                installment_amount=installment_value,
                total_installments=transaction.total_installments,
                current_installment=transaction.current_installment,
                card_id=transaction.card_id,
                card_name=card_label,
                paid_by_user_id=owner_id,
                paid_by_user_name=user_name_by_id.get(owner_id, f"Usuário {owner_id}"),
                paid_from_family_pool=is_family_payer,
                splits=(
                    []
                    if is_family_payer
                    else [
                        TransactionSplitDetail(
                            user_id=split.user_id,
                            user_name=user_name_by_id.get(
                                split.user_id, f"Usuário {split.user_id}"
                            ),
                            split_value=split.split_value,
                        )
                        for split in tx_splits
                    ]
                ),
            )
        )

    transaction_details.sort(key=lambda item: item.transaction_date, reverse=True)

    spending_by_category: list[CategorySpending] = []
    if total_spent > 0:
        for category, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
            spending_by_category.append(
                CategorySpending(
                    category=category,
                    total=amount,
                    percentage=float((amount / total_spent) * 100),
                )
            )

    spending_by_card: list[CardSpending] = []
    if total_spent > 0:
        for card_id, amount in sorted(card_totals.items(), key=lambda item: item[1], reverse=True):
            card = card_by_id.get(card_id)
            if not card:
                continue
            spending_by_card.append(
                CardSpending(
                    card_id=card_id,
                    card_name=card_display_name(card),
                    user_id=card.user_id,
                    user_name=user_name_by_id.get(card.user_id, f"Usuário {card.user_id}"),
                    total=amount,
                    percentage=float((amount / total_spent) * 100),
                    transaction_count=card_transaction_counts.get(card_id, 0),
                )
            )

    limits = list(
        session.exec(select(SpendingLimit).where(SpendingLimit.month_year == month_year)).all()
    )
    limit_progress: list[LimitProgress] = []
    for limit in limits:
        spent = (
            total_spent
            if limit.category is None
            else category_totals.get(limit.category, Decimal("0.00"))
        )
        percentage = float((spent / limit.limit_value) * 100) if limit.limit_value > 0 else 0.0
        limit_progress.append(
            LimitProgress(
                category=limit.category,
                limit_value=limit.limit_value,
                spent=spent,
                percentage=percentage,
                alert_level=_alert_level(spent, limit.limit_value),
            )
        )

    budgets = list(
        session.exec(select(MonthlyBudget).where(MonthlyBudget.month_year == month_year)).all()
    )
    budget_by_user = {budget.user_id: budget for budget in budgets}

    member_balances: list[MemberBalance] = []
    total_contributions = Decimal("0.00")

    for user in users:
        budget = budget_by_user.get(user.id)
        actual = budget.actual_contribution if budget else Decimal("0.00")
        if (
            budget
            and actual == Decimal("0.00")
            and budget.expected_contribution > Decimal("0.00")
        ):
            actual = budget.expected_contribution

        if user.is_family:
            total_contributions += actual
            continue

        card_others = card_spent_for_others.get(user.id, Decimal("0.00"))
        individual = individual_expenses.get(user.id, Decimal("0.00"))

        balance = actual + card_others - individual
        total_contributions += actual

        member_balances.append(
            MemberBalance(
                user_id=user.id,
                user_name=user.name,
                actual_contribution=actual,
                card_spent_for_others=card_others,
                individual_expenses=individual,
                balance=balance,
            )
        )

    transfer_suggestions = _compute_pairwise_card_transfers(
        transactions,
        splits_by_transaction,
        card_by_id,
        family_user_ids,
        user_name_by_id,
    )
    family_pool_balance = total_contributions - family_pool_spent
    personal_card_spent = total_spent - family_pool_spent
    payment_checklist = get_checklist_status(session, month_year)

    return MonthlyDashboard(
        month_year=month_year,
        total_spent=total_spent,
        total_contributions=total_contributions,
        family_pool_spent=family_pool_spent,
        family_pool_balance=family_pool_balance,
        personal_card_spent=personal_card_spent,
        spending_by_category=spending_by_category,
        spending_by_card=spending_by_card,
        transaction_details=transaction_details,
        limit_progress=limit_progress,
        member_balances=member_balances,
        transfer_suggestions=transfer_suggestions,
        payment_checklist=payment_checklist,
    )
