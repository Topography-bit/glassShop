from fastapi import APIRouter, HTTPException

from app.users.dao import UserDAO
from app.users.schemas import SUserAuth, SUserRead
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/registration", response_model=SUserRead, summary="Регистрация")
async def register(data: SUserAuth):
    """
    Регистрация пользователя.

    **Параметры:**
        - `email`: уникальный адрес почты.
        - `password`: пароль в незахешированном виде

    **Возвращает:**
        - `Профиль пользователя` по схеме SUserRead.
    
    **Ошибки:**
        - `409 Conflict`: если пользователь с таким email уже существует.
    """
    existing_user = await UserDAO.find_one_or_none(email=data.email)

    if existing_user: 
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
    
    hashed_password = hash_password(data.password)

    user = await UserDAO.add_and_return(email=data.email, hashed_password=hashed_password)
    
    return user