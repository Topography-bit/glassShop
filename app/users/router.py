from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from jose import ExpiredSignatureError, JWTError, jwt

from app.security import (
    ACCESS_TOKEN_EXPIRE,
    ALGORITHM,
    SECRET_KEY,
    auth_cookie_kwargs,
    clear_auth_cookies,
    create_access_token,
    generate_code,
    hash_password,
    send_verify_email,
    set_cookies,
    verify_password,
)
from app.users.dao import UserDAO
from app.users.dependencies import get_current_user
from app.users.schemas import SResendVerifyCode, SUserAuth, SUserConfirmEmail, SUserRead


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/registration")
async def register(data: SUserAuth, background_tasks: BackgroundTasks):
    existing_user = await UserDAO.find_one_or_none(email=data.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")

    plain_code = generate_code()
    now = datetime.now(timezone.utc)

    await UserDAO.add(
        email=data.email,
        hashed_password=hash_password(data.password),
        verify_code_hash=hash_password(plain_code),
        verify_code_expires_at=now + timedelta(minutes=10),
        verify_code_sent_at=now,
    )

    background_tasks.add_task(send_verify_email, data.email, plain_code)
    return {
        "message": "Пользователь создан. Код подтверждения отправлен на почту.",
        "email": data.email,
    }


@router.post("/registration/confirm", response_model=SUserRead)
async def confirm_registration(data: SUserConfirmEmail, response: Response):
    user = await UserDAO.find_one_or_none(email=data.email)

    if not user:
        raise HTTPException(status_code=404, detail="Неверные данные")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Вход запрещен")

    if user.is_verified:
        set_cookies(response, user.id)
        return user

    if not user.verify_code_hash or not user.verify_code_expires_at:
        raise HTTPException(status_code=400, detail="Код не был запрошен или истек")

    if user.attempts >= 5:
        await UserDAO.update(
            filter_by={"id": user.id},
            verify_code_hash=None,
            verify_code_expires_at=None,
            attempts=0,
        )
        raise HTTPException(
            status_code=429,
            detail="Вы исчерпали количество попыток. Запросите новый код.",
        )

    if datetime.now(timezone.utc) > user.verify_code_expires_at:
        await UserDAO.update(
            filter_by={"id": user.id},
            verify_code_hash=None,
            verify_code_expires_at=None,
            attempts=0,
        )
        raise HTTPException(status_code=400, detail="Срок действия кода истек")

    if not verify_password(data.code, user.verify_code_hash):
        current_attempts = user.attempts + 1
        await UserDAO.update(filter_by={"id": user.id}, attempts=current_attempts)
        attempts_left = max(0, 5 - current_attempts)
        raise HTTPException(
            status_code=400,
            detail=f"Неверный код подтверждения, осталось попыток {attempts_left}",
        )

    verified_user = await UserDAO.update(
        filter_by={"id": user.id},
        is_verified=True,
        verify_code_hash=None,
        verify_code_expires_at=None,
        attempts=0,
    )

    set_cookies(response, verified_user.id)
    return verified_user


@router.post("/registration/resend_verify_code")
async def resend_verify_code(data: SResendVerifyCode, background_tasks: BackgroundTasks):
    user = await UserDAO.find_one_or_none(email=data.email)

    if not user:
        raise HTTPException(status_code=404, detail="Неверные данные")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if user.is_verified:
        return {"message": "Почта уже подтверждена."}

    now = datetime.now(timezone.utc)
    if user.verify_code_sent_at and now - user.verify_code_sent_at < timedelta(minutes=3):
        raise HTTPException(status_code=429, detail="Подождите 3 минуты перед отправкой нового кода.")

    plain_code = generate_code()
    await UserDAO.update(
        filter_by={"id": user.id},
        verify_code_hash=hash_password(plain_code),
        verify_code_expires_at=now + timedelta(minutes=10),
        verify_code_sent_at=now,
        attempts=0,
    )

    background_tasks.add_task(send_verify_email, data.email, plain_code)
    return {"message": "Код был успешно отправлен на указанный вами email."}


@router.post("/login", response_model=SUserRead)
async def login(response: Response, data: SUserAuth):
    user = await UserDAO.find_one_or_none(email=data.email)

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неправильный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email не подтвержден")

    set_cookies(response, user.id)
    return user


@router.get("/me", response_model=SUserRead)
async def get_me(user=Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response):
    clear_auth_cookies(response)


@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response):
    refresh = request.cookies.get("refresh")

    if not refresh:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Срок действия refresh token истек")

    try:
        payload = jwt.decode(token=refresh, key=SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Срок действия refresh token истек")
    except JWTError:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    if payload.get("type") != "refresh":
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    user_id = payload.get("sub")
    if not user_id:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    user = await UserDAO.find_one_or_none(id=user_id)
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    if not user.is_active:
        clear_auth_cookies(response)
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    access = create_access_token({"sub": str(user_id)})
    response.set_cookie(
        key="access",
        value=access,
        **auth_cookie_kwargs(max_age=ACCESS_TOKEN_EXPIRE * 60),
    )

    return {"message": "Session refreshed"}
