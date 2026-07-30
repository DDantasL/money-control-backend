import logging
import time
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.services.auth_service import ensure_initial_admin
from app.services.family_service import ensure_family_account
from app.models import (
    Account,
    ContributionExtra,
    MonthlyBudget,
    PaymentCard,
    PaymentChecklistItem,
    RecurringContribution,
    RecurringPayment,
    RecurringPaymentSkip,
    SpendingLimit,
    Transaction,
    TransactionSplit,
    User,
)

# Referência explícita para evitar F401: estes imports são usados apenas para
# registrar tabelas no SQLModel metadata (create_all).
_models_for_metadata_registration = (
    Account,
    MonthlyBudget,
    ContributionExtra,
    PaymentCard,
    PaymentChecklistItem,
    RecurringContribution,
    RecurringPayment,
    RecurringPaymentSkip,
    SpendingLimit,
    Transaction,
    TransactionSplit,
    User,
)

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    """Aguarda o PostgreSQL ficar disponível antes de criar as tabelas."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Conexão com o banco estabelecida.")
            return
        except OperationalError as error:
            if attempt == max_attempts:
                raise RuntimeError(
                    "Não foi possível conectar ao PostgreSQL. "
                    "Verifique se o container está rodando: docker compose up -d"
                ) from error
            logger.warning(
                "Banco indisponível (tentativa %s/%s). Tentando novamente em %ss...",
                attempt,
                max_attempts,
                delay_seconds,
            )
            time.sleep(delay_seconds)


def _migrate_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if "users" in table_names:
        columns = {column["name"] for column in inspector.get_columns("users")}
        with engine.begin() as connection:
            if "email" in columns:
                connection.execute(text("ALTER TABLE users DROP COLUMN email"))
                logger.info("Coluna users.email removida.")
            if "is_family" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN is_family BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
                logger.info("Coluna users.is_family adicionada.")

    if "payment_cards" in table_names:
        columns = {column["name"] for column in inspector.get_columns("payment_cards")}
        with engine.begin() as connection:
            if "last_four_digits" in columns:
                connection.execute(text("ALTER TABLE payment_cards DROP COLUMN last_four_digits"))
                logger.info("Coluna payment_cards.last_four_digits removida.")
            if "nickname" not in columns:
                connection.execute(
                    text("ALTER TABLE payment_cards ADD COLUMN nickname VARCHAR(100)")
                )
                logger.info("Coluna payment_cards.nickname adicionada.")
            if "active" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE payment_cards ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE"
                    )
                )
                logger.info("Coluna payment_cards.active adicionada.")

    if "transactions" in table_names and "recurring_payments" in table_names:
        columns = {column["name"] for column in inspector.get_columns("transactions")}
        with engine.begin() as connection:
            if "recurring_payment_id" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE transactions ADD COLUMN recurring_payment_id INTEGER "
                        "REFERENCES recurring_payments(id)"
                    )
                )
                logger.info("Coluna transactions.recurring_payment_id adicionada.")


def create_db_and_tables() -> None:
    wait_for_database()
    SQLModel.metadata.create_all(engine)
    _migrate_schema()
    with Session(engine) as session:
        ensure_family_account(session)
        ensure_initial_admin(session)
    logger.info("Tabelas verificadas/criadas com sucesso.")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
