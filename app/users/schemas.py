from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field

mail = Annotated[EmailStr, Field(..., description="Электронная почта")]


class SUserAuth(BaseModel):
    email: mail
    password: str = Field(..., min_length=5, max_length=50, description="Пароль")


class SUserConfirmEmail(BaseModel):
    email: mail
    code: str = Field(..., description="6-ти значный код подтверждения")


class SResendVerifyCode(BaseModel):
    email: mail


class SUserRead(BaseModel):
    id: int = Field(..., ge=1)
    email: mail
    is_admin: bool
    is_active: bool
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
