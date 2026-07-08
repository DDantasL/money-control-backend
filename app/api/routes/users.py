from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import User
from app.schemas.transaction import UserCreate, UserRead, UserUpdate
from app.services.delete_service import delete_user
from app.services.family_service import FAMILY_USER_NAME
from app.services.update_service import update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(session: Session = Depends(get_session)) -> list[User]:
    return list(session.exec(select(User).order_by(User.is_family.desc(), User.name)).all())


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_session)) -> User:
    if payload.name.strip().lower() == FAMILY_USER_NAME.lower():
        raise HTTPException(status_code=400, detail="Use o pagador Família do sistema para o caixa coletivo.")

    user = User(name=payload.name.strip())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def patch_user(
    user_id: int,
    payload: UserUpdate,
    session: Session = Depends(get_session),
) -> User:
    return update_user(session, user_id, payload)


@router.delete("/{user_id}", status_code=204)
def remove_user(user_id: int, session: Session = Depends(get_session)) -> None:
    delete_user(session, user_id)
