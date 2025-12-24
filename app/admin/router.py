from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.admin.dependencies import user_is_admin
from app.admin.service import parse_categories_of_products, parse_products_by_names
from app.products.dao import CategoriesDAO, ProductsDAO

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(user_is_admin)])


@router.post("/add_all_products", summary="Загрузить все товары",
             description=(
    "Добавляет все категории и товары из excel-файла в БД.\n\n"
    "Обязательные поля в excel-файле: (достаточно, чтобы название колонки начиналось с ключевого слова):\n"
        "- Категория (ключевое слово \"катег\")\n"
        "- Название (ключевое слово \"назв\")\n"
        "- Цена (ключевое слово \"цена\")\n"
    "Не обязательные: \n"
        "- Размеры (Ширина*Высота, ключевое слово \"формат\")"
    ))
async def add_all_products(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Нужен .xlsx файл")
    
    read_bytes = await file.read()

    categories = parse_categories_of_products(read_bytes)
    products = parse_products_by_names(read_bytes)

    try:
        await ProductsDAO.delete_bulk()
        await CategoriesDAO.delete_bulk()
        await CategoriesDAO.add_bulk(categories)

        cata_db = await CategoriesDAO.get_all()

        catas_map = {
            c.category_name: c.id for c in cata_db
        }

        for product in products:
            product["category_id"] = catas_map[product["category_name"]]
            product.pop("category_name")

        await ProductsDAO.add_bulk(products)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка при добавлении")

    return {"message": "Все товары успешно добавлены"}