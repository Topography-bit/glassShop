from io import BytesIO
from fastapi import HTTPException
import openpyxl


def parse_products_by_names(file_bytes: bytes) -> list[dict]:
    """Считывает продукты и возвращает в удобном формате для массовой вставки.

    **Параметры**:
        - file_bytes - байты файла

    **Возвращает**:
        - Список из словарей со всеми необходимыми значениями для удобной вставки товаров.
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    work_sheet = wb.active
    
    name_idx, price_idx, width_idx, category_idx, thickness_idx = -1, -1, -1, -1, -1

    for idx, cell in enumerate(work_sheet[1]):
        val = cell.value
        val = val.strip().lower() if isinstance(val, str) else ""
        if val.startswith("назв"):
            name_idx = idx
        elif val.startswith("цена"):
            price_idx = idx
        elif val.startswith("формат"):
            width_idx = idx
        elif val.startswith("катег"):
            category_idx = idx
        elif val.startswith("толщина"):
            thickness_idx = idx   
    if name_idx == -1 or price_idx == -1 or category_idx == -1:
        raise HTTPException(status_code=400, detail="Нет одной из необходимых колонок")

    ans = []

    for r in work_sheet.iter_rows(min_row=2, values_only=True):
        name = r[name_idx] + f" {r[thickness_idx]} мм" if thickness_idx != -1 and r[thickness_idx] != None else r[name_idx]
        price = r[price_idx]
        wl = r[width_idx] if width_idx != -1 else None
        category_name = r[category_idx]
        category_name = category_name.strip() if isinstance(category_name, str) else category_name
        wl = wl.strip() if isinstance(wl, str) else ""

        if "*" in wl:
            width, length = map(str.strip, wl.split("*", 1))
        else:
            width, length = None, None

        ans.append({"name": name, "price_per_m2": price, "max_width": width, "max_length": length, "category_name": category_name})

    return ans


def parse_categories_of_products(file_bytes: bytes):
    """Считывает категории продуктов и возвращает в удобном формате для массовой вставки.

    **Параметры**:
        - file_bytes - байты файла

    **Возвращает**:
        - Список из словарей со значениями "category_name" для удобной вставки 
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active

    headers = []
    categories_col_id = -1

    for cell in ws[1]:
        val = cell.value or ""
        headers.append(str(val).strip().lower())

    for i in range(len(headers)):
        if headers[i].startswith("катег"):
            categories_col_id = i + 1
            break

    if categories_col_id == -1:
        raise HTTPException(status_code=400, detail="Нет колонок с категориями")

    repeats = set()
    lst = []
    for r in ws.iter_rows(min_row=2, min_col=categories_col_id, max_col=categories_col_id, values_only=True):
        if r[0] is not None and str(r[0]).strip() != "" and str(r[0]) not in repeats:
            lst.append({"category_name": str(r[0])})  
            repeats.add(str(r[0]))
        else:
            continue

    if not lst:
        raise HTTPException(status_code=400, detail="Нет категорий товара")
    
    return lst