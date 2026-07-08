from decimal import Decimal, ROUND_HALF_UP

from app.schemas.transaction import TransactionSplitCreate


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def split_evenly(total: Decimal, user_ids: list[int]) -> list[TransactionSplitCreate]:
    if not user_ids:
        raise ValueError("Informe ao menos um usuário para dividir a compra.")

    per_user = quantize(total / len(user_ids))
    splits = [TransactionSplitCreate(user_id=user_id, split_value=per_user) for user_id in user_ids]

    remainder = total - sum(s.split_value for s in splits)
    if remainder != Decimal("0.00") and splits:
        splits[0] = TransactionSplitCreate(
            user_id=splits[0].user_id,
            split_value=splits[0].split_value + remainder,
        )
    return splits
