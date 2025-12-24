from fastapi import FastAPI, HTTPException

from app.users.router import router as auth_router
from app.admin.router import router as admin_router
from app.products.router import router as products_router

app = FastAPI(
    title="GlassShop",
    description="Магазин по продаже стекла",
    version="v1"
    )

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_router)