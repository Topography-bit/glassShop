from fastapi import FastAPI, HTTPException
from app.users.router import router as auth_router

app = FastAPI(
    title="GlassShop",
    description="Магазин по продаже стекла",
    version="v1"
    )

app.include_router(auth_router)