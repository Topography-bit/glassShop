from fastapi import APIRouter, HTTPException, Response

from app.users.dao import UserDAO
from app.users.schemas import SUserAuth, SUserRead
from app.security import ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE, create_access_token, create_refresh_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/registration", response_model=SUserRead, summary="Регистрация", 
    description=(
    "Регистрация пользователя.\n\n"
    "**Параметры:**\n\n"
        "- **email**: уникальный адрес почты.\n"
        "- **password**: пароль в незахешированном виде.\n\n"
    "**Возвращает:**\n\n"
        "- **Профиль пользователя** по схеме SUserRead.\n\n"
    "**Ошибки:**\n\n"
        "- **409**: если пользователь с таким email уже существует.\n")
        )
async def register(data: SUserAuth):

    existing_user = await UserDAO.find_one_or_none(email=data.email)

    if existing_user: 
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
    
    hashed_password = hash_password(data.password)

    user = await UserDAO.add_and_return(email=data.email, hashed_password=hashed_password)
    
    return user


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

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response.set_cookie(key="access", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE*60)
    response.set_cookie(key="refresh", value=refresh_token, httponly=True, max_age=REFRESH_TOKEN_EXPIRE* 24 * 60 * 60)

    return user