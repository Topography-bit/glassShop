from decimal import Decimal
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.products.dao import CategoriesDAO, EdgesDAO, FacetsDAO, ProductsDAO, TemperingDAO
from app.database import new_session
from app.products.models import EdgeProcessingPrice, FacetPrice, TemperingPrice
from app.products.schemas import ConfigSchema, PriceResponse, ProductSchema
from app.products.service import calc_price

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


@router.get("/products/{product_id}/config", response_model=ConfigSchema, summary="Данные для конфигуратора товара",
        description=("Возвращает инфу о товаре и список подходящих услуг"
                "на основе толщины стекла, а также доступности."))
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

    async with new_session() as session:

        edges = await session.execute(select(EdgeProcessingPrice).filter_by(thickness_mm=product.thickness_mm, is_active=True))
        edges = edges.scalars().all()
        facets = await session.execute(select(FacetPrice).filter_by(is_active=True))
        facets = facets.scalars().all()
        tempering = await session.execute(select(TemperingPrice).filter_by(thickness_mm=product.thickness_mm, is_active=True))
        tempering = tempering.scalars().all()


    return {
            "product": product,
            "edges": edges,
            "facets": facets,
            "temperings": tempering,
        }