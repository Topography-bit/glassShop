from __future__ import annotations

import math
import re
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
    importance: float = 0.0
    addresstype: str | None = None


_GEOCODER_CACHE: dict[str, GeoPoint] = {}
_GEOCODER_SUGGEST_CACHE: dict[str, list[GeoPoint]] = {}
_SUGGESTION_LIMIT = 8
_LOCALITY_ADDRESS_TYPES = frozenset(
    {
        "administrative",
        "borough",
        "city",
        "city_district",
        "county",
        "district",
        "hamlet",
        "isolated_dwelling",
        "municipality",
        "neighbourhood",
        "province",
        "quarter",
        "region",
        "settlement",
        "state",
        "suburb",
        "town",
        "village",
    }
)


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
    origin_name = settings.DELIVERY_ORIGIN_NAME.strip()
    if origin_name and origin_name.casefold() not in lowered:
        queries.append(f"{origin_name}, {normalized_address}")

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

    try:
        importance = float(raw_point.get("importance") or 0.0)
    except (TypeError, ValueError):
        importance = 0.0

    addresstype = raw_point.get("addresstype")
    if addresstype is not None:
        addresstype = str(addresstype).strip() or None

    return GeoPoint(
        display_name=display_name,
        lat=lat,
        lon=lon,
        importance=importance,
        addresstype=addresstype,
    )


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


def _normalize_geocoder_text(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]+", " ", value.casefold()).split())


def _score_geocoder_point(point: GeoPoint, query: str) -> tuple[int, int, int, int, float, int]:
    title, _ = _split_display_name(point.display_name)
    normalized_query = _normalize_geocoder_text(query)
    normalized_title = _normalize_geocoder_text(title)
    normalized_display_name = _normalize_geocoder_text(point.display_name)

    exact_title_match = int(bool(normalized_query) and normalized_title == normalized_query)
    locality_match = int((point.addresstype or "").casefold() in _LOCALITY_ADDRESS_TYPES)
    title_prefix_match = int(bool(normalized_query) and normalized_title.startswith(normalized_query))
    display_prefix_match = int(
        bool(normalized_query) and normalized_display_name.startswith(normalized_query)
    )

    return (
        exact_title_match,
        locality_match,
        title_prefix_match,
        display_prefix_match,
        point.importance,
        -abs(len(normalized_title) - len(normalized_query)),
    )


def _sort_geocoder_points(points: list[GeoPoint], query: str) -> list[GeoPoint]:
    return sorted(points, key=lambda point: _score_geocoder_point(point, query), reverse=True)


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
        # Suggestions should search across Russia first so city queries like
        # "Краснодар" are not trapped inside the local delivery-radius box.
        points = await _request_geocoder(normalized_query, bounded=False, limit=_SUGGESTION_LIMIT)
        deduped_points = _dedupe_points(points)

        if len(deduped_points) < _SUGGESTION_LIMIT:
            for search_query in _build_geocoder_queries(normalized_query):
                if search_query == normalized_query:
                    continue

                points.extend(
                    await _request_geocoder(
                        search_query,
                        bounded=False,
                        limit=_SUGGESTION_LIMIT,
                    )
                )
                deduped_points = _dedupe_points(points)
                if len(deduped_points) >= _SUGGESTION_LIMIT:
                    break

        if len(deduped_points) < _SUGGESTION_LIMIT:
            for search_query in _build_geocoder_queries(normalized_query):
                points.extend(
                    await _request_geocoder(
                        search_query,
                        bounded=True,
                        limit=_SUGGESTION_LIMIT,
                    )
                )
                deduped_points = _dedupe_points(points)
                if len(deduped_points) >= _SUGGESTION_LIMIT:
                    break

        cached = _sort_geocoder_points(deduped_points, normalized_query)[:_SUGGESTION_LIMIT]
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
