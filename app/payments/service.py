from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import settings


MONEY_PRECISION = Decimal("0.01")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def ensure_yookassa_settings() -> None:
    missing = []

    if not settings.YOOKASSA_SHOP_ID:
        missing.append("YOOKASSA_SHOP_ID")

    if not settings.YOOKASSA_SECRET_KEY:
        missing.append("YOOKASSA_SECRET_KEY")

    if not settings.YOOKASSA_RETURN_URL:
        missing.append("YOOKASSA_RETURN_URL")

    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "ЮKassa не настроена. Заполните переменные окружения: "
                + ", ".join(missing)
            ),
        )


def build_yookassa_return_url(order_id: int) -> str:
    ensure_yookassa_settings()
    split_result = urlsplit(settings.YOOKASSA_RETURN_URL or "")
    query_items = dict(parse_qsl(split_result.query, keep_blank_values=True))
    query_items["payment_order_id"] = str(order_id)

    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query_items),
            split_result.fragment,
        )
    )


def payment_order_message(status: str, payment_status: str) -> str:
    if status == "paid":
        return "Оплата подтверждена. Заказ сохранен и передан в обработку."

    if status == "canceled" or payment_status == "canceled":
        return "Платеж отменен. Можно вернуться к корзине и создать оплату заново."

    if status == "failed":
        return "Не удалось создать или завершить платеж. Проверьте настройки и попробуйте снова."

    return "Платеж создан. Завершите оплату в ЮKassa, чтобы подтвердить заказ."


async def create_yookassa_payment(
    *,
    order_id: int,
    amount: Decimal,
    description: str,
    metadata: dict[str, str],
) -> dict:
    ensure_yookassa_settings()

    payload = {
        "amount": {
            "value": f"{money(amount):.2f}",
            "currency": settings.YOOKASSA_CURRENCY,
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": build_yookassa_return_url(order_id),
        },
        "description": description,
        "metadata": metadata,
    }
    headers = {"Idempotence-Key": str(uuid4())}

    try:
        async with httpx.AsyncClient(
            base_url=settings.YOOKASSA_API_BASE_URL,
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
            timeout=20.0,
        ) as client:
            response = await client.post("/payments", json=payload, headers=headers)
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="Не удалось связаться с API ЮKassa. Проверьте сеть и параметры магазина.",
        ) from error

    if response.is_error:
        error_detail = "ЮKassa отклонила запрос на создание платежа."
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            description = payload.get("description")
            if isinstance(description, str) and description.strip():
                error_detail = f"ЮKassa: {description.strip()}"

        raise HTTPException(status_code=502, detail=error_detail)

    created_payment = response.json()
    confirmation_url = created_payment.get("confirmation", {}).get("confirmation_url")

    if not confirmation_url:
        raise HTTPException(
            status_code=502,
            detail="ЮKassa вернула платеж без ссылки подтверждения. Проверьте тип confirmation.",
        )

    return created_payment


async def get_yookassa_payment(payment_id: str) -> dict:
    ensure_yookassa_settings()

    try:
        async with httpx.AsyncClient(
            base_url=settings.YOOKASSA_API_BASE_URL,
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
            timeout=20.0,
        ) as client:
            response = await client.get(f"/payments/{payment_id}")
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="Не удалось получить статус платежа из ЮKassa.",
        ) from error

    return response.json()
