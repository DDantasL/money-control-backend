from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    if not any(character.isalpha() for character in password):
        raise ValueError("A senha deve conter pelo menos uma letra.")
    if not any(character.isdigit() for character in password):
        raise ValueError("A senha deve conter pelo menos um número.")
    return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SetupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountRead(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class AuthStatusResponse(BaseModel):
    setup_required: bool
