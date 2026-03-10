from decimal import Decimal
from io import BytesIO

import openpyxl
from fastapi import HTTPException


def parse_products_by_names(file_bytes: bytes) -> list[dict]:
    """Read products from an xlsx file for bulk upsert."""
    workbook = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    worksheet = workbook.active

    name_idx, price_idx, format_idx, category_idx, thickness_idx, image_idx = -1, -1, -1, -1, -1, -1

    for idx, cell in enumerate(worksheet[1]):
        value = cell.value
        value = value.strip().lower() if isinstance(value, str) else ""

        if value.startswith("назв"):
            name_idx = idx
        elif value.startswith("цена"):
            price_idx = idx
        elif value.startswith("формат"):
            format_idx = idx
        elif value.startswith("катег"):
            category_idx = idx
        elif value.startswith("толщина"):
            thickness_idx = idx
        elif (
            "фото" in value
            or "изображ" in value
            or "картин" in value
            or "image" in value
            or "photo" in value
            or value == "img"
        ):
            image_idx = idx

    if name_idx == -1 or price_idx == -1 or category_idx == -1:
        raise HTTPException(status_code=400, detail="Нет одной из необходимых колонок")

    products: list[dict] = []

    for row in worksheet.iter_rows(min_row=2):
        thickness = row[thickness_idx].value if thickness_idx != -1 else None
        raw_name = row[name_idx].value

        if raw_name is None:
            continue

        name = raw_name if thickness is None else f"{raw_name} {thickness} мм"
        price = Decimal(str(row[price_idx].value))
        raw_format = row[format_idx].value if format_idx != -1 else None
        category_name = row[category_idx].value
        category_name = category_name.strip() if isinstance(category_name, str) else category_name
        format_value = raw_format.strip() if isinstance(raw_format, str) else ""

        image_url = None
        if image_idx != -1:
            image_cell = row[image_idx]
            if image_cell.hyperlink is not None and image_cell.hyperlink.target:
                image_url = image_cell.hyperlink.target.strip() or None
            elif isinstance(image_cell.value, str):
                image_url = image_cell.value.strip() or None

        if "*" in format_value:
            width, length = map(str.strip, format_value.split("*", 1))
            max_width = int(width)
            max_length = int(length)
        else:
            max_width, max_length = None, None

        products.append(
            {
                "name": name,
                "image_url": image_url,
                "thickness_mm": thickness,
                "price_per_m2": price,
                "max_width": max_width,
                "max_length": max_length,
                "category_name": category_name,
            }
        )

    return products


def parse_categories_of_products(file_bytes: bytes):
    """Read unique product categories from an xlsx file."""
    workbook = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    worksheet = workbook.active

    headers = []
    categories_col_id = -1

    for cell in worksheet[1]:
        value = cell.value or ""
        headers.append(str(value).strip().lower())

    for index, header in enumerate(headers, start=1):
        if header.startswith("катег"):
            categories_col_id = index
            break

    if categories_col_id == -1:
        raise HTTPException(status_code=400, detail="Нет колонок с категориями")

    seen = set()
    categories = []
    for row in worksheet.iter_rows(
        min_row=2,
        min_col=categories_col_id,
        max_col=categories_col_id,
        values_only=True,
    ):
        if row[0] is None:
            continue

        category_name = str(row[0]).strip()
        if category_name == "" or category_name.lower() in seen:
            continue

        categories.append({"category_name": category_name})
        seen.add(category_name.lower())

    if not categories:
        raise HTTPException(status_code=400, detail="Нет категорий товара")

    return categories
