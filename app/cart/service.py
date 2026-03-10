from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import httpx
from fastapi import HTTPException

from app.config import settings
from app.products.dao import EdgesDAO, FacetsDAO, ProductsDAO, TemperingDAO
from app.products.service import calc_price


MONEY_PRECISION = Decimal("0.01")
_GEOCODER_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(slots=True)
class GeoPoint:
    display_name: str
    lat: float
    lon: float


_GEOCODER_CACHE: dict[str, GeoPoint] = {}
_GEOCODER_SUGGEST_CACHE: dict[str, list[GeoPoint]] = {}


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def _distance_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    inner = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(inner), math.sqrt(1 - inner))


def _distance_from_origin_km(point: GeoPoint) -> float:
    return _haversine_km(
        settings.DELIVERY_ORIGIN_LAT,
        settings.DELIVERY_ORIGIN_LON,
        point.lat,
        point.lon,
    )


def _delivery_viewbox() -> str:
    lat_delta = settings.DELIVERY_MAX_RADIUS_KM / 111.0
    lon_base = 111.0 * max(0.2, math.cos(math.radians(settings.DELIVERY_ORIGIN_LAT)))
    lon_delta = settings.DELIVERY_MAX_RADIUS_KM / lon_base

    left = settings.DELIVERY_ORIGIN_LON - lon_delta
    top = settings.DELIVERY_ORIGIN_LAT + lat_delta
    right = settings.DELIVERY_ORIGIN_LON + lon_delta
    bottom = settings.DELIVERY_ORIGIN_LAT - lat_delta
    return f"{left},{top},{right},{bottom}"


def _build_geocoder_queries(address: str) -> list[str]:
    normalized_address = " ".join(address.split())
    lowered = normalized_address.casefold()

    queries = [normalized_address]
    if not any(token in lowered for token in ("майкоп", "maikop", "адыге", "adyg")):
        queries.insert(0, f"{settings.DELIVERY_ORIGIN_NAME}, {normalized_address}")

    return list(dict.fromkeys(query for query in queries if query))


def _parse_geocoder_result(raw_point: dict, fallback_address: str) -> GeoPoint | None:
    try:
        lat = float(raw_point["lat"])
        lon = float(raw_point["lon"])
    except (KeyError, TypeError, ValueError):
        return None

    display_name = str(raw_point.get("display_name") or fallback_address).strip()
    if not display_name:
        return None

    return GeoPoint(display_name=display_name, lat=lat, lon=lon)


def _dedupe_points(points: list[GeoPoint]) -> list[GeoPoint]:
    unique_points: list[GeoPoint] = []
    seen: set[tuple[str, int, int]] = set()

    for point in points:
        key = (
            point.display_name.casefold(),
            round(point.lat * 100000),
            round(point.lon * 100000),
        )
        if key in seen:
            continue

        seen.add(key)
        unique_points.append(point)

    return unique_points


def _split_display_name(display_name: str) -> tuple[str, str | None]:
    parts = [part.strip() for part in display_name.split(",") if part.strip()]

    if not parts:
        return display_name, None

    title = parts[0]
    subtitle = ", ".join(parts[1:]) or None
    return title, subtitle


async def _request_geocoder(address: str, *, bounded: bool, limit: int) -> list[GeoPoint]:
    params: dict[str, str | int] = {
        "q": address,
        "format": "jsonv2",
        "limit": limit,
        "countrycodes": "ru",
        "accept-language": "ru",
        "dedupe": 1,
    }

    if settings.GEOCODER_CONTACT_EMAIL:
        params["email"] = settings.GEOCODER_CONTACT_EMAIL

    if bounded:
        params["viewbox"] = _delivery_viewbox()
        params["bounded"] = 1

    headers = {
        "User-Agent": "GlassSelling/1.0 delivery-check",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(_GEOCODER_URL, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="Не удалось связаться с сервисом расчета доставки. Попробуйте еще раз.",
        ) from error

    payload = response.json()
    if not payload:
        return []

    points: list[GeoPoint] = []
    for raw_point in payload[:limit]:
        point = _parse_geocoder_result(raw_point, address)
        if point is not None:
            points.append(point)

    return _dedupe_points(points)


async def resolve_delivery_address(address: str) -> GeoPoint:
    normalized_address = " ".join(address.split())

    if len(normalized_address) < 5:
        raise HTTPException(
            status_code=400,
            detail="Укажи адрес доставки подробнее: населенный пункт, улицу и дом.",
        )

    cached = _GEOCODER_CACHE.get(normalized_address.lower())
    if cached is not None:
        return cached

    for bounded in (True, False):
        for query in _build_geocoder_queries(normalized_address):
            points = await _request_geocoder(query, bounded=bounded, limit=1)
            if points:
                _GEOCODER_CACHE[normalized_address.lower()] = points[0]
                return points[0]

    raise HTTPException(
        status_code=400,
        detail="Не удалось определить адрес. Укажи населенный пункт, улицу и номер дома.",
    )


async def suggest_delivery_addresses(query: str) -> list[dict]:
    normalized_query = " ".join(query.split())

    if len(normalized_query) < 3:
        return []

    cache_key = normalized_query.lower()
    cached = _GEOCODER_SUGGEST_CACHE.get(cache_key)

    if cached is None:
        points: list[GeoPoint] = []

        for search_query in _build_geocoder_queries(normalized_query):
            points.extend(await _request_geocoder(search_query, bounded=True, limit=5))

        if len(points) < 5:
            for search_query in _build_geocoder_queries(normalized_query):
                points.extend(await _request_geocoder(search_query, bounded=False, limit=5))

        cached = _dedupe_points(points)[:5]
        _GEOCODER_SUGGEST_CACHE[cache_key] = cached

    suggestions: list[dict] = []
    for point in cached:
        distance_km = _distance_from_origin_km(point)
        title, subtitle = _split_display_name(point.display_name)

        suggestions.append(
            {
                "title": title,
                "subtitle": subtitle,
                "full_address": point.display_name,
                "distance_km": _distance_decimal(distance_km),
                "within_radius": distance_km <= settings.DELIVERY_MAX_RADIUS_KM,
                "lat": point.lat,
                "lon": point.lon,
            }
        )

    return suggestions


def build_delivery_quote(*, address: str, point: GeoPoint, subtotal: Decimal, items_available: bool) -> dict:
    distance_km = _distance_from_origin_km(point)
    distance_value = _distance_decimal(distance_km)
    within_radius = distance_km <= settings.DELIVERY_MAX_RADIUS_KM

    if within_radius:
        billed_km = Decimal(max(1, math.ceil(distance_km)))
        distance_component = settings.DELIVERY_PRICE_PER_KM * billed_km
        delivery_price = _money(max(settings.DELIVERY_MIN_PRICE, distance_component))
        message = (
            f"Адрес входит в зону доставки. Расстояние от {settings.DELIVERY_ORIGIN_NAME}: "
            f"{distance_value} км."
        )
    else:
        delivery_price = Decimal("0.00")
        message = (
            f"Адрес находится в {distance_value} км от {settings.DELIVERY_ORIGIN_NAME}. "
            f"Доставка доступна только в радиусе {settings.DELIVERY_MAX_RADIUS_KM:.0f} км."
        )

    total_price = _money(subtotal + delivery_price)

    return {
        "address": address,
        "normalized_address": point.display_name,
        "distance_km": distance_value,
        "delivery_price": delivery_price,
        "subtotal_price": _money(subtotal),
        "total_price": total_price,
        "within_radius": within_radius,
        "can_order": items_available and within_radius,
        "message": message,
    }


async def validate_item_in_cart(item) -> tuple[bool, str | None, Decimal, bool]:
    is_available = True
    error_message = None
    current_price = item.price
    price_changed = False

    edge_price = Decimal("0.00")
    facet_price = Decimal("0.00")
    tempering_price = Decimal("0.00")

    product = await ProductsDAO.find_one_or_none(id=item.product_id)

    if not product or not product.is_active:
        return False, "Товар больше недоступен", current_price, price_changed

    if item.edge_id is not None:
        edge = await EdgesDAO.find_one_or_none(id=item.edge_id)

        if not edge or not edge.is_active:
            return False, "Обработка края больше недоступна", current_price, price_changed

        if edge.thickness_mm != product.thickness_mm:
            return False, "Обработка края больше не подходит к товару", current_price, price_changed

        edge_price = edge.price

    if item.facet_id is not None:
        facet = await FacetsDAO.find_one_or_none(id=item.facet_id)

        if not facet or not facet.is_active:
            return False, "Фацет больше недоступен", current_price, price_changed

        facet_price = facet.price

    if item.tempering_id is not None:
        tempering = await TemperingDAO.find_one_or_none(id=item.tempering_id)

        if not tempering or not tempering.is_active:
            return False, "Закалка больше недоступна", current_price, price_changed

        if tempering.thickness_mm != product.thickness_mm:
            return False, "Закалка больше не подходит к товару", current_price, price_changed

        tempering_price = tempering.price

    new_price = calc_price(
        product_price=product.price_per_m2,
        width_mm=item.width_mm,
        length_mm=item.length_mm,
        qty=item.quantity,
        edge_price=edge_price,
        facet_price=facet_price,
        tempering_price=tempering_price,
    )

    price_changed = new_price != item.price
    return is_available, error_message, new_price, price_changed


async def check_edge_facet_tempering(
    *,
    product,
    edge_id: int | None = None,
    facet_id: int | None = None,
    tempering_id: int | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    edge_price = Decimal("0.00")
    facet_price = Decimal("0.00")
    tempering_price = Decimal("0.00")

    if edge_id is not None:
        edge = await EdgesDAO.find_one_or_none(id=edge_id)

        if (
            edge is None
            or edge.thickness_mm != product.thickness_mm
            or not edge.is_active
            or edge.thickness_mm != product.thickness_mm
        ):
            raise HTTPException(status_code=400, detail="Недоступная обработка края для данного товара")

        edge_price = edge.price

    if facet_id is not None:
        facet = await FacetsDAO.find_one_or_none(id=facet_id)

        if facet is None or not facet.is_active:
            raise HTTPException(status_code=400, detail="Такого фацета не существует")

        facet_price = facet.price

    if tempering_id is not None:
        tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

        if (
            tempering is None
            or tempering.thickness_mm != product.thickness_mm
            or not tempering.is_active
            or tempering.thickness_mm != product.thickness_mm
        ):
            raise HTTPException(status_code=400, detail="Недоступная закалка товара")

        tempering_price = tempering.price

    return (edge_price, facet_price, tempering_price)
