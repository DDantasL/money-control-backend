from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session

from app.database import get_session
from app.models import Account
from app.services.auth_service import decode_access_token, get_account_by_id

security = HTTPBearer(auto_error=False)


def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: Session = Depends(get_session),
) -> Account:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        account_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    account = get_account_by_id(session, account_id)
    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta inativa ou inexistente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return account
