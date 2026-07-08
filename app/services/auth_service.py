from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import text
from sqlmodel import Session, select

from app.config import settings
from app.models import Account

SETUP_LOCK_ID = 42_069_001
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"timing-safe-dummy", bcrypt.gensalt()).decode("utf-8")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(account_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(account_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, str]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def get_account_by_email(session: Session, email: str) -> Account | None:
    return session.exec(select(Account).where(Account.email == normalize_email(email))).first()


def get_account_by_id(session: Session, account_id: int) -> Account | None:
    return session.get(Account, account_id)


def create_account_in_session(
    session: Session,
    email: str,
    password: str,
    *,
    commit: bool = True,
) -> Account:
    account = Account(
        email=normalize_email(email),
        password_hash=hash_password(password),
    )
    session.add(account)
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(account)
    return account


def create_account(session: Session, email: str, password: str) -> Account:
    return create_account_in_session(session, email, password, commit=True)


def create_initial_account(session: Session, email: str, password: str) -> Account:
    """Cria a primeira conta com lock transacional para evitar race condition."""
    session.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": SETUP_LOCK_ID})

    if has_any_account(session):
        raise ValueError("A conta inicial já foi configurada.")

    return create_account_in_session(session, email, password, commit=False)


def authenticate_account(session: Session, email: str, password: str) -> Account | None:
    account = get_account_by_email(session, email)
    password_hash = account.password_hash if account and account.is_active else _DUMMY_PASSWORD_HASH

    if not verify_password(password, password_hash):
        return None

    return account if account and account.is_active else None


def has_any_account(session: Session) -> bool:
    return session.exec(select(Account.id).limit(1)).first() is not None


def ensure_initial_admin(session: Session) -> None:
    if has_any_account(session):
        return
    if not settings.initial_admin_email or not settings.initial_admin_password:
        return
    create_initial_account(session, settings.initial_admin_email, settings.initial_admin_password)
    session.commit()
