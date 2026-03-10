from fastapi import APIRouter, HTTPException

from app.products.dao import CategoriesDAO, ProductsDAO
from app.products.schemas import ConfigSchema, ProductSchema
from app.products.service import edges_facets_temperings_product

router = APIRouter(prefix="/categories", tags=["Products"])


@router.get("", summary="Получить все категории")
async def get_all_categories():
    return await CategoriesDAO.get_all()


@router.get(
    "/{category_id}/products",
    response_model=list[ProductSchema],
    summary="Получить все товары по категории",
)
async def get_products_by_category(category_id: int):
    category = await CategoriesDAO.find_one_or_none(id=category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    return await ProductsDAO.get_all_by(category_id=category_id)


@router.get(
    "/products/{product_id}/config",
    response_model=ConfigSchema,
    summary="Данные для конфигуратора товара",
    description=(
        "Возвращает информацию о товаре и список подходящих услуг "
        "на основе толщины стекла, а также их доступности."
    ),
)
async def product_configurator(product_id: int):
    product = await ProductsDAO.find_one_or_none(id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Нет товара с таким id")

    if product.thickness_mm is None:
        return {
            "product": product,
            "edges": [],
            "facets": [],
            "temperings": [],
        }

    edges, facets, temperings = await edges_facets_temperings_product(product=product)

    return {
        "product": product,
        "edges": edges,
        "facets": facets,
        "temperings": temperings,
    }
