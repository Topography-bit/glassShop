from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.admin.router import router as admin_router
from app.cart.router import router as carts_router
from app.products.router import router as products_router
from app.users.router import router as auth_router


app = FastAPI(
    title="GlassShop",
    description="РњР°РіР°Р·РёРЅ РїРѕ РїСЂРѕРґР°Р¶Рµ СЃС‚РµРєР»Р°",
    version="v1",
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(products_router)
app.include_router(carts_router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "glass-selling" / "browser"
api_prefixes = ("auth", "admin", "categories", "cart")


if frontend_dist.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith(api_prefixes):
            raise HTTPException(status_code=404)

        requested_file = frontend_dist / full_path

        if full_path and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(frontend_dist / "index.html")
