from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException

from app.cart.dao import CartsDAO
from app.cart.schemas import SCartResponse
from app.products.dao import EdgesDAO, FacetsDAO, ProductsDAO, TemperingDAO
from app.products.schemas import PriceResponse
from app.products.service import calc_price
from app.users.dependencies import get_current_user


router = APIRouter(prefix="/cart", tags=["Cart"], dependencies=[Depends(get_current_user)])


@router.post("/cart", summary="Корзина пользователя", response_model=SCartResponse, status_code=201,
        description=(
        "Добавляет товар в корзину пользователя.\n\n"
        "Если в корзине уже есть позиция с тем же товаром, размерами и опциями "
        "(обработка края, фацет, закалка), то количество увеличивается, а цена пересчитывается.\n\n"
        "Перед добавлением выполняются проверки:\n"
        "- размеры находятся в допустимых пределах;\n"
        "- товар существует;\n"
        "- выбранные опции доступны и активны.\n\n"
        "Возвращает актуальное состояние позиции корзины."
    ))
async def products_cart(product_id: int, width_mm: int, length_mm: int, qty: int = 1, edge_id: int | None = None, 
            facet_id: int | None = None, tempering_id: int | None = None, user = Depends(get_current_user)) -> dict:
    
    product = await ProductsDAO.find_one_or_none(id=product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Такого товара нет в наличии")
    
    if (width_mm > product.max_width 
        or width_mm < product.min_width 
        or length_mm > product.max_length 
        or length_mm < product.min_length):
        raise HTTPException(status_code=400, detail="Недопустимые длина или ширина")

    edge_price, facet_price, tempering_price = 0, 0, 0

    if product.thickness_mm:
        if edge_id is not None:
            edge = await EdgesDAO.find_one_or_none(id=edge_id)

            if edge is None or edge.thickness_mm != product.thickness_mm or not edge.is_active:
                raise HTTPException(status_code=400, detail="Недоступная обработка края для данного товара")
            edge_price = edge.price

        if facet_id is not None:
            facet = await FacetsDAO.find_one_or_none(id=facet_id)

            if facet is None or not facet.is_active:
                raise HTTPException(status_code=400, detail="Такого фацета не существует")
            facet_price = facet.price

        if tempering_id is not None:
            tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

            if tempering is None or tempering.thickness_mm != product.thickness_mm or not tempering.is_active:
                raise HTTPException(status_code=400, detail="Недоступная закалка товара")
            tempering_price = tempering.price


    
    existing = await CartsDAO.find_one_or_none(user_id=user.id, product_id=product_id, width_mm=width_mm, 
        length_mm=length_mm, edge_id=edge_id, facet_id=facet_id, tempering_id=tempering_id)

    if existing:
        new_qty = existing.quantity + qty

        new_price = calc_price(product_price=product.price_per_m2, width_mm=width_mm, length_mm=length_mm,
            edge_price=edge_price, facet_price=facet_price, tempering_price=tempering_price, qty=new_qty)
        
        new_cart = await CartsDAO.update({"id": existing.id}, quantity=new_qty, price=new_price)

        return new_cart
    else:
        price = calc_price(product_price=product.price_per_m2, width_mm=width_mm, length_mm=length_mm, 
            edge_price=edge_price, tempering_price=tempering_price, facet_price=facet_price, qty=qty)
        
        cart = await CartsDAO.add_and_return(user_id=user.id, product_id=product.id, width_mm=width_mm, 
            length_mm=length_mm, quantity=qty, price=price, 
            edge_id=edge_id, facet_id=facet_id, tempering_id=tempering_id)
        
        return cart


@router.get("/cart", description=(
        "Возвращает текущую корзину авторизованного пользователя.\n\n"
        "Ответ содержит:\n"
        "- список всех позиций корзины;\n"
        "- общую стоимость корзины."
    ))
async def get_cart(user=Depends(get_current_user)):
    items = await CartsDAO.get_all_by(user_id=user.id)
    total = Decimal("0.00")

    for i in items: total += i.price

    return {"items": items, "total price": total}