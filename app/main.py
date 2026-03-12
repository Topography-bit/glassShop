from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.admin.router import router as admin_router
from app.cart.router import router as carts_router
from app.config import settings
from app.database import new_session
from app.payments.router import router as payments_router
from app.products.router import router as products_router
from app.users.router import router as auth_router


app = FastAPI(
    title="GlassShop",
    description="Каталог и заказ стекла с административной панелью и оплатой.",
    version="v1",
)

cors_origins = [
    origin.strip()
    for origin in settings.BACKEND_CORS_ORIGINS.split(",")
    if origin.strip()
]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_router)
app.include_router(carts_router)
app.include_router(payments_router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "glass-selling" / "browser"
media_dir = Path(__file__).resolve().parent.parent / "media"
api_prefixes = ("auth", "admin", "categories", "cart", "payments")

media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")


def _is_api_path(full_path: str) -> bool:
    return any(full_path == prefix or full_path.startswith(f"{prefix}/") for prefix in api_prefixes)


async def _serve_frontend_file(full_path: str):
    if _is_api_path(full_path):
        raise HTTPException(status_code=404)

    requested_file = frontend_dist / full_path

    if full_path and requested_file.is_file():
        return FileResponse(requested_file)

    return FileResponse(frontend_dist / "index.html")


@app.get("/healthz", tags=["Health"])
async def healthcheck():
    async with new_session() as session:
        await session.execute(text("SELECT 1"))

    return {"status": "ok", "environment": settings.APP_ENV}


if frontend_dist.exists():
    @app.get("/", include_in_schema=False)
    async def serve_frontend_root():
        return await _serve_frontend_file("")


    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return await _serve_frontend_file(full_path)
