from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi import BackgroundTasks
from jose import JWTError, jwt

from app.users.dao import UserDAO
from app.users.dependencies import get_current_user
from app.users.schemas import SResendVerifyCode, SUserAuth, SUserConfirmEmail, SUserRead
from app.security import ACCESS_TOKEN_EXPIRE, ALGORITHM, REFRESH_TOKEN_EXPIRE, SECRET_KEY, create_access_token, create_refresh_token, hash_password, send_verify_email, set_cookies, verify_password, generate_code

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/registration", summary="Регистрация", 
    description=(
    "Регистрация пользователя. Отправка кода подтверждения на email.\n\n"
    "**Параметры:**\n\n"
        "- **email**: уникальный адрес почты.\n"
        "- **password**: пароль в незахешированном виде.\n\n"
    "**Ошибки:**\n\n"
        "- **409**: если пользователь с таким email уже существует.\n")
        )
async def register(data: SUserAuth, background_tasks: BackgroundTasks):

    existing_user = await UserDAO.find_one_or_none(email=data.email)

    if existing_user: 
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
    
    hashed_password = hash_password(data.password)
    plain_code = generate_code()
    hash_code = hash_password(plain_code)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)
    
    await UserDAO.add(
        email=data.email, 
        hashed_password=hashed_password,
        verify_code_hash=hash_code,
        verify_code_expires_at=expires_at,
        verify_code_sent_at=now
        )

    background_tasks.add_task(send_verify_email, data.email, plain_code)
    
    return {
        "message": "Пользователь создан. Код подтверждения отправлен на почту.",
        "email": data.email
    }


@router.post("/registration/confirm", response_model=SUserRead, summary="Подтверждение кода",
    description=(
    "Подтверждение почты отправленным на email кодом.\n\n"
    "**Параметры:**\n\n"
        "- **email**: уникальный адрес почты.\n"
        "- **code**: код отправленный на почту.\n\n"
    "**Поведение:**\n\n"
        "- При успешном подтверждении устанавливает cookies **access** и **refresh**.\n\n"
    "**Ошибки:**\n\n"
        "- **400**: нет кода, он указан неверно или срок его действия истек.\n"
        "- **403**: доступ запрещен.\n"
        "- **404**: неверный email.\n"
        "- **429**: слишком много попыток ввода.\n"
        ))
async def confirm_registration(data: SUserConfirmEmail, response: Response):
    user = await UserDAO.find_one_or_none(email=data.email)

    if not user:
        raise HTTPException(status_code=404, detail="Неверные данные")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Вход запрещен!")

    if user.is_verified:
        set_cookies(response, user.id)
        return user

    if not user.verify_code_hash or not user.verify_code_expires_at:
        raise HTTPException(status_code=400, detail="Код не был запрошен или истек")

    if user.attempts >= 5:
        await UserDAO.update(
            filter_by={'id': user.id},
            verify_code_hash=None,
            verify_code_expires_at=None,
            attempts=0
            )
        raise HTTPException(
            status_code=429, 
            detail="Вы исчерпали количество попыток. Запросите новый код."
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

        await UserDAO.update(
            filter_by={'id': user.id},
            attempts=current_attempts
            )
        
        attempts_left = 5 - current_attempts

        raise HTTPException(status_code=400, detail=f"Неверный код подтверждения, осталось попыток {attempts_left}")


    new_user = await UserDAO.update(
        filter_by={"id": user.id},
        is_verified=True,
        verify_code_hash=None,
        verify_code_expires_at=None,
        attempts=0
    )
    
    set_cookies(response, new_user.id)

    return new_user


@router.post("/registration/resend_verify_code", summary="Переотправка кода подтверждения",
    description=(
    "Переотправка кода подтверждения почты.\n\n"
    "**Параметры:**\n\n"
        "- **email**: уникальный адрес почты.\n\n"
    "**Ошибки:**\n\n"
        "- **403**: доступ запрещен.\n"
        "- **404**: неверный email.\n"
        "- **429**: не прошло еще 3 минуты с момента отправки старого.\n"
        ))    
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
    hash_code = hash_password(plain_code)

    await UserDAO.update(
        filter_by={"id": user.id},
        verify_code_hash=hash_code,
        verify_code_expires_at=now + timedelta(minutes=10),
        verify_code_sent_at=now,
        attempts=0,
    )

    background_tasks.add_task(send_verify_email, data.email, plain_code)

    return {"message": "Код был успешно отправлен на указанный вами email."}


@router.post("/login", response_model=SUserRead, summary="Вход",
            description=(
    "Выполняет вход пользователя. Создает access и refresh токены.\n\n"
    "**Параметры:**\n\n"
        "- email: зарегистрированный адрес почты.\n"
        "- password: пароль в незахешированном виде.\n\n"
    "**Возвращает:**\n\n"
        "- Устанавливает токены в Cookies, устанавливая access и refresh токены.\n"
        "- Профиль пользователя по схеме SUserRead.\n\n"
    "**Ошибки:**\n\n"
        "- 401: если неверный пароль или человек с таким email не зарегистрирован.\n")
    )
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


@router.get("/me", summary="Текущий пользователь", response_model=SUserRead, 
            description="Возвращает данные пользователя по схеме SUserRead")
async def get_me(user = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204, summary="Выход из учетной записи",  
               description="Выход из учетной записи")
async def logout(response: Response):
    response.delete_cookie("access")
    response.delete_cookie("refresh")


@router.post("/refresh", status_code=204, summary="Refresh access token\'а", 
             description="Создает новый access token по истечению старого")
async def refresh_access_token(request: Request, response: Response):

    refresh = request.cookies.get("refresh")

    if not refresh:
        raise HTTPException(status_code=401, detail="Refresh token истек")

    try:
        payload = jwt.decode(token=refresh, key=SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный refresh token") 

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    try: 
        user_id = int(user_id)
    except (ValueError, TypeError): 
        raise HTTPException(status_code=401, detail="Невалидный refresh token")

    user = await UserDAO.find_one_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=401)
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    access = create_access_token({"sub": user_id})

    response.set_cookie(key="access", value=access, httponly=True, max_age=ACCESS_TOKEN_EXPIRE*60)
