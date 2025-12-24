from fastapi import APIRouter, HTTPException

from app.products.dao import CategoriesDAO, ProductsDAO

router = APIRouter(prefix="/categories", tags=["Products"])


@router.get("", summary="Получить все категории")
async def get_all_categories():
    return await CategoriesDAO.get_all()


@router.get("/{category_id}/products", summary="Получить все товары по категории")
async def get_products_by_category(category_id: int):
    category = await CategoriesDAO.find_one_or_none(id=category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    return await ProductsDAO.get_all_by(category_id=category_id)


@router.get("/products/{product_id}/config", summary="Конфигуратор, открывающийся когда пользователь нажимает на товар")
async def product_configurator(product_id):
    