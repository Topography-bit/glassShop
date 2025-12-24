from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SUserAuth(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль")


class SUserConfirmEmail(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    code: str = Field(..., description="6-ти значный код подтверждения")


class SResendVerifyCode(BaseModel):
    email: EmailStr


class SUserRead(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)