from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request

from app.cart.dao import CartsDAO
from app.cart.service import GeoPoint, build_delivery_quote, resolve_delivery_address, validate_item_in_cart
from app.payments.dao import OrdersDAO
from app.payments.schemas import SPaymentOrderOut, SYooKassaCheckoutIn
from app.payments.service import (
    create_yookassa_payment,
    ensure_yookassa_settings,
    get_yookassa_payment,
    payment_order_message,
    utc_now,
)
from app.products.dao import ProductsDAO
from app.users.dependencies import get_current_user
from app.config import settings


router = APIRouter(prefix="/payments", tags=["Payments"])


def _serialize_order(order) -> dict:
    return {
        "order_id": order.id,
        "provider": order.provider,
        "status": order.status,
        "payment_status": order.payment_status,
        "currency": order.currency,
        "subtotal_price": order.subtotal_price,
        "delivery_price": order.delivery_price,
        "total_price": order.total_price,
        "confirmation_url": order.confirmation_url,
        "paid_at": order.paid_at,
        "message": payment_order_message(order.status, order.payment_status),
    }


def _cart_item_ids_from_payload(items_payload: list[dict]) -> list[int]:
    item_ids: list[int] = []

    for item in items_payload:
        cart_item_id = item.get("cart_item_id")
        if isinstance(cart_item_id, int) and cart_item_id > 0:
            item_ids.append(cart_item_id)

    return item_ids


async def _sync_order_from_payment_payload(order, payment_payload: dict) -> None:
    event = payment_payload.get("event")
    payment_object = payment_payload.get("object") if event else payment_payload

    if not isinstance(payment_object, dict):
        return

    next_payment_status = str(payment_object.get("status") or order.payment_status)
    next_status = order.status
    paid_at = order.paid_at
    should_clear_items = False

    if next_payment_status == "succeeded" or event == "payment.succeeded":
        if order.status != "paid":
            next_status = "paid"
            paid_at = utc_now()
            should_clear_items = True
    elif next_payment_status == "canceled" or event == "payment.canceled":
        next_status = "canceled"
    elif next_payment_status in {"pending", "waiting_for_capture"}:
        next_status = "pending"

    await OrdersDAO.update(
        {"id": order.id},
        status=next_status,
        payment_status=next_payment_status,
        provider_payload=payment_payload,
        paid_at=paid_at,
        updated_at=utc_now(),
    )

    if should_clear_items:
        cart_item_ids = _cart_item_ids_from_payload(order.items_payload)
        await CartsDAO.delete_items(user_id=order.user_id, item_ids=cart_item_ids)


@router.post("/yookassa/create", response_model=SPaymentOrderOut)
async def create_yookassa_checkout(data: SYooKassaCheckoutIn, user=Depends(get_current_user)):
    ensure_yookassa_settings()

    items = sorted(await CartsDAO.get_all_by(user_id=user.id), key=lambda item: item.id)
    if not items:
        raise HTTPException(status_code=400, detail="Корзина пуста. Сначала добавьте товары.")

    if (data.lat is None) != (data.lon is None):
        raise HTTPException(
            status_code=400,
            detail="Передайте либо обе координаты адреса, либо не передавайте их вовсе.",
        )

    subtotal = Decimal("0.00")
    items_available = True
    snapshot_items: list[dict] = []

    for item in items:
        product = await ProductsDAO.find_one_or_none(id=item.product_id)
        is_available, error_message, current_price, price_changed = await validate_item_in_cart(item)
        subtotal += current_price

        if not is_available:
            items_available = False

        snapshot_items.append(
            {
                "cart_item_id": item.id,
                "product_id": item.product_id,
                "name": product.name if product else f"Материал #{item.product_id}",
                "width_mm": item.width_mm,
                "length_mm": item.length_mm,
                "quantity": item.quantity,
                "edge_id": item.edge_id,
                "facet_id": item.facet_id,
                "tempering_id": item.tempering_id,
                "current_price": f"{current_price:.2f}",
                "is_available": is_available,
                "price_changed": price_changed,
                "error_message": error_message,
            }
        )

    if not items_available:
        raise HTTPException(
            status_code=400,
            detail="В корзине есть недоступные позиции. Исправьте их перед оплатой.",
        )

    if data.lat is not None and data.lon is not None:
        point = GeoPoint(
            display_name=(data.normalized_address or data.address).strip(),
            lat=data.lat,
            lon=data.lon,
        )
    else:
        point = await resolve_delivery_address(data.address)

    delivery_quote = build_delivery_quote(
        address=data.address.strip(),
        point=point,
        subtotal=subtotal,
        items_available=items_available,
    )

    if not delivery_quote["can_order"]:
        raise HTTPException(
            status_code=400,
            detail=delivery_quote["message"] or "Заказ нельзя оплатить в текущем состоянии.",
        )

    timestamp = utc_now()
    order = await OrdersDAO.add_and_return(
        user_id=user.id,
        provider="yookassa",
        status="pending",
        payment_status="pending",
        currency=settings.YOOKASSA_CURRENCY,
        subtotal_price=delivery_quote["subtotal_price"],
        delivery_price=delivery_quote["delivery_price"],
        total_price=delivery_quote["total_price"],
        delivery_distance_km=delivery_quote["distance_km"],
        delivery_address=delivery_quote["address"],
        delivery_normalized_address=delivery_quote["normalized_address"],
        items_payload=snapshot_items,
        provider_payload=None,
        created_at=timestamp,
        updated_at=timestamp,
    )

    try:
        created_payment = await create_yookassa_payment(
            order_id=order.id,
            amount=order.total_price,
            description=f"Заказ #{order.id} на GlassSelling",
            metadata={
                "order_id": str(order.id),
                "user_id": str(user.id),
            },
        )
    except HTTPException:
        await OrdersDAO.update(
            {"id": order.id},
            status="failed",
            payment_status="failed",
            updated_at=utc_now(),
        )
        raise

    confirmation = created_payment.get("confirmation", {})
    order = await OrdersDAO.update(
        {"id": order.id},
        payment_status=str(created_payment.get("status") or "pending"),
        yookassa_payment_id=str(created_payment.get("id")),
        confirmation_url=confirmation.get("confirmation_url"),
        provider_payload=created_payment,
        updated_at=utc_now(),
    )

    if order.payment_status == "succeeded":
        await _sync_order_from_payment_payload(order, created_payment)
        order = await OrdersDAO.find_one_or_none(id=order.id, user_id=user.id)

    return _serialize_order(order)


@router.get("/orders/{order_id}", response_model=SPaymentOrderOut)
async def get_payment_order(order_id: int, user=Depends(get_current_user)):
    order = await OrdersDAO.find_one_or_none(id=order_id, user_id=user.id)

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден.")

    if order.status == "pending" and order.yookassa_payment_id:
        try:
            payment_payload = await get_yookassa_payment(order.yookassa_payment_id)
        except HTTPException:
            payment_payload = None

        if payment_payload is not None:
            await _sync_order_from_payment_payload(order, payment_payload)
            order = await OrdersDAO.find_one_or_none(id=order.id, user_id=user.id)

    return _serialize_order(order)


@router.post("/yookassa/webhook/{webhook_token}")
async def handle_yookassa_webhook(webhook_token: str, request: Request):
    expected_token = settings.YOOKASSA_WEBHOOK_TOKEN

    if not expected_token or webhook_token != expected_token:
        raise HTTPException(status_code=404, detail="Webhook не найден.")

    payload = await request.json()
    payment_object = payload.get("object")
    payment_id = payment_object.get("id") if isinstance(payment_object, dict) else None

    if not payment_id:
        return {"ok": True}

    order = await OrdersDAO.find_one_or_none(yookassa_payment_id=str(payment_id))
    if not order:
        return {"ok": True}

    try:
        payment_payload = await get_yookassa_payment(str(payment_id))
    except HTTPException:
        return {"ok": True}

    await _sync_order_from_payment_payload(order, payment_payload)
    return {"ok": True}
