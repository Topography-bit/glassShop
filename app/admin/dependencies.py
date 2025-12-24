from fastapi import Depends, HTTPException

from app.users.dependencies import get_current_user


async def user_is_admin(user = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Вход запрещен")
    
    return user