from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.cart.dao import CartsDAO
from app.cart.schemas import (
    SCartAdd,
    SCartChangeQty,
    SCartDeliveryQuoteIn,
    SCartDeliveryQuoteOut,
    SCartDeliverySuggestionOut,
    SCartItemResponse,
)
from app.cart.service import (
    GeoPoint,
    build_delivery_quote,
    check_edge_facet_tempering,
    resolve_delivery_address,
    suggest_delivery_addresses,
    validate_item_in_cart,
)
from app.products.dao import ProductsDAO
from app.products.service import calc_price
from app.users.dependencies import get_current_user


router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("", response_model=SCartItemResponse, status_code=201)
async def products_cart(data: SCartAdd, user=Depends(get_current_user)) -> dict:
    product = await ProductsDAO.find_one_or_none(id=data.product_id)
    edge_price = Decimal("0.00")
    facet_price = Decimal("0.00")
    tempering_price = Decimal("0.00")

    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Такого товара нет в наличии")

    if (
        data.width_mm is None
        or data.length_mm is None
        or product.min_width is None
        or product.max_width is None
        or product.min_length is None
        or product.max_length is None
    ):
        raise HTTPException(status_code=400, detail="Для этого товара онлайн-расчет пока недоступен")

    if (
        data.width_mm > product.max_width
        or data.width_mm < product.min_width
        or data.length_mm > product.max_length
        or data.length_mm < product.min_length
    ):
        raise HTTPException(status_code=400, detail="Недопустимые длина или ширина")

    if product.thickness_mm is not None:
        edge_price, facet_price, tempering_price = await check_edge_facet_tempering(
            product=product,
            edge_id=data.edge_id,
            facet_id=data.facet_id,
            tempering_id=data.tempering_id,
        )

    existing = await CartsDAO.find_one_or_none(
        user_id=user.id,
        product_id=data.product_id,
        width_mm=data.width_mm,
        length_mm=data.length_mm,
        edge_id=data.edge_id,
        facet_id=data.facet_id,
        tempering_id=data.tempering_id,
    )

    if existing:
        new_qty = existing.quantity + data.qty
        new_price = calc_price(
            product_price=product.price_per_m2,
            width_mm=data.width_mm,
            length_mm=data.length_mm,
            edge_price=edge_price,
            facet_price=facet_price,
            tempering_price=tempering_price,
            qty=new_qty,
        )
        return await CartsDAO.update({"id": existing.id}, quantity=new_qty, price=new_price)

    price = calc_price(
        product_price=product.price_per_m2,
        width_mm=data.width_mm,
        length_mm=data.length_mm,
        edge_price=edge_price,
        tempering_price=tempering_price,
        facet_price=facet_price,
        qty=data.qty,
    )

    return await CartsDAO.add_and_return(
        user_id=user.id,
        product_id=product.id,
        width_mm=data.width_mm,
        length_mm=data.length_mm,
        quantity=data.qty,
        price=price,
        edge_id=data.edge_id,
        facet_id=data.facet_id,
        tempering_id=data.tempering_id,
    )


@router.get("")
async def get_cart(user=Depends(get_current_user)):
    items = sorted(await CartsDAO.get_all_by(user_id=user.id), key=lambda item: item.id)
    response_items = []
    total = Decimal("0.00")
    can_order = True

    for item in items:
        is_available, error_message, current_price, price_changed = await validate_item_in_cart(item)

        if not is_available:
            can_order = False

        total += current_price

        response_items.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "width_mm": item.width_mm,
                "length_mm": item.length_mm,
                "quantity": item.quantity,
                "edge_id": item.edge_id,
                "facet_id": item.facet_id,
                "tempering_id": item.tempering_id,
                "start_price": item.price,
                "current_price": current_price,
                "is_available": is_available,
                "price_changed": price_changed,
                "error_message": error_message,
            }
        )

    return {"items": response_items, "total_price": total, "can_order": can_order}


@router.get("/delivery/suggest", response_model=list[SCartDeliverySuggestionOut])
async def get_delivery_suggestions(q: str, user=Depends(get_current_user)):
    return await suggest_delivery_addresses(q)


@router.post("/delivery/quote", response_model=SCartDeliveryQuoteOut)
async def quote_delivery(data: SCartDeliveryQuoteIn, user=Depends(get_current_user)):
    items = sorted(await CartsDAO.get_all_by(user_id=user.id), key=lambda item: item.id)

    if not items:
        raise HTTPException(status_code=400, detail="Корзина пуста. Сначала добавь товары.")

    subtotal = Decimal("0.00")
    items_available = True

    for item in items:
        is_available, _, current_price, _ = await validate_item_in_cart(item)
        subtotal += current_price
        if not is_available:
            items_available = False

    if (data.lat is None) != (data.lon is None):
        raise HTTPException(status_code=400, detail="Передай либо обе координаты адреса, либо не передавай их вовсе.")

    if data.lat is not None and data.lon is not None:
        point = GeoPoint(
            display_name=(data.normalized_address or data.address).strip(),
            lat=data.lat,
            lon=data.lon,
        )
    else:
        point = await resolve_delivery_address(data.address)

    return build_delivery_quote(
        address=data.address.strip(),
        point=point,
        subtotal=subtotal,
        items_available=items_available,
    )


@router.delete("/{cart_item_id}", status_code=204)
async def delete_from_cart(cart_item_id: int, user=Depends(get_current_user)):
    item = await CartsDAO.find_one_or_none(id=cart_item_id, user_id=user.id)

    if not item:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    await CartsDAO.delete_by(id=cart_item_id, user_id=user.id)


@router.patch("/change_qty", response_model=SCartItemResponse)
async def change_qty(data: SCartChangeQty, user=Depends(get_current_user)):
    cart_prod = await CartsDAO.find_one_or_none(id=data.cart_prod_id, user_id=user.id)

    if not cart_prod:
        raise HTTPException(status_code=404, detail="Товар в корзине не найден")

    product = await ProductsDAO.find_one_or_none(id=cart_prod.product_id)

    if not product or not product.is_active:
        raise HTTPException(status_code=400, detail="Товар недоступен")

    edge_price = Decimal("0.00")
    facet_price = Decimal("0.00")
    tempering_price = Decimal("0.00")

    if product.thickness_mm is not None:
        edge_price, facet_price, tempering_price = await check_edge_facet_tempering(
            product=product,
            edge_id=cart_prod.edge_id,
            facet_id=cart_prod.facet_id,
            tempering_id=cart_prod.tempering_id,
        )

    new_price = calc_price(
        product_price=product.price_per_m2,
        width_mm=cart_prod.width_mm,
        length_mm=cart_prod.length_mm,
        qty=data.qty,
        edge_price=edge_price,
        facet_price=facet_price,
        tempering_price=tempering_price,
    )

    return await CartsDAO.update({"id": cart_prod.id}, quantity=data.qty, price=new_price)


@router.delete("", status_code=204)
async def clear_cart(user=Depends(get_current_user)):
    await CartsDAO.delete_by(user_id=user.id)
