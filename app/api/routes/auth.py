from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.api.deps import get_current_account
from app.database import get_session
from app.models import Account
from app.schemas.auth import (
    AccountRead,
    AuthStatusResponse,
    LoginRequest,
    SetupRequest,
    TokenResponse,
)
from app.services.auth_service import (
    authenticate_account,
    create_access_token,
    create_initial_account,
    has_any_account,
)
from app.services.rate_limit_service import clear_rate_limit, enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(session: Session = Depends(get_session)) -> AuthStatusResponse:
    return AuthStatusResponse(setup_required=not has_any_account(session))


@router.post("/setup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def setup_account(
    payload: SetupRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TokenResponse:
    enforce_rate_limit(request, "auth:setup")

    try:
        with session.begin():
            account = create_initial_account(session, payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    clear_rate_limit(request, "auth:setup")
    token = create_access_token(account.id or 0, account.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TokenResponse:
    enforce_rate_limit(request, "auth:login")

    account = authenticate_account(session, payload.email, payload.password)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    clear_rate_limit(request, "auth:login")
    token = create_access_token(account.id or 0, account.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AccountRead)
def get_me(account: Account = Depends(get_current_account)) -> Account:
    return account
