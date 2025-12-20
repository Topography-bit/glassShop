from fastapi import HTTPException, Request
from jose import jwt, JWTError, ExpiredSignatureError

from app.security import ALGORITHM, SECRET_KEY
from app.users.dao import UserDAO


async def get_current_user(request: Request):
    """Dependency: возвращает текущего авторизованного пользователя по access JWT из cookies.
    Бросает HTTPException(401), если пользователь не авторизован.
    """
    token = request.cookies.get("access")

    if not token: 
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    try:
        payload = jwt.decode(token=token, key=SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except JWTError:
        raise HTTPException(status_code=401, detail="Не авторизован")

    id = payload.get("sub")
    if not id:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user = await UserDAO.find_one_or_none(id=int(id))
    if not user: 
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    return user