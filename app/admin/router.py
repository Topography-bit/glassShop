from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.admin.dependencies import user_is_admin
from app.products.schemas import SEdgeOut, SEdgeUpdate, SFacetOut, SFacetUpdate, STemperingOut, STemperingUpdate
from app.admin.service import parse_categories_of_products, parse_products_by_names
from app.products.dao import CategoriesDAO, EdgesDAO, FacetsDAO, ProductsDAO, TemperingDAO

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


@router.post("/edges", summary="Создать новую обработку края", status_code=201,
        description="Добавляет тип обработки края в базу. Используется в админ-панели.")
async def add_edge(data: SEdgeUpdate):
    
    edge = await EdgesDAO.add_and_return(**data.model_dump())
    
    return edge


@router.get("/edges/{edge_id}", response_model=SEdgeOut, summary="Получить данные обработки края",
        description="Возвращает данные обработки края по id.")
async def get_edge_data(edge_id: int):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)

    if not edge:
        raise HTTPException(status_code=404, detail="Обработка не найдена")
    
    return edge


@router.put("/edges/{edge_id}", response_model=SEdgeOut, summary="Обновить обработку края",
        description="Полное обновление данных обработки края. Заменяет все существующие поля.")
async def update_edge(edge_id: int, data: SEdgeUpdate):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Обработка не найдена")

    updated = await EdgesDAO.update({"id": edge_id}, **data.model_dump())

    return updated


@router.delete("/edges/{edge_id}", status_code=204, summary="Удалить обработку края",
        description="Удаляет обработку края по id.")
async def delete_edge(edge_id: int):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Обработка не найдена")
    
    await EdgesDAO.delete_by(id=edge_id)


@router.post("/facets", summary="Создать новый фацет", status_code=201,
        description="Добавляет фацет в базу. Используется в админ-панели.")
async def add_facet(data: SFacetUpdate):
    facet = await FacetsDAO.add_and_return(**data.model_dump())

    return facet


@router.get("/facets/{facet_id}", response_model=SFacetOut, summary="Получить данные фацета",
        description="Возвращает данные фацета по id.")
async def get_facet_data(facet_id: int):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)

    if not facet:
        raise HTTPException(status_code=404, detail="Фацет не найден")
    
    return facet


@router.put("/facets/{facet_id}", response_model=SFacetOut, summary="Обновить фацет",
        description="Полное обновление данных фацета. Заменяет все существующие поля.")
async def update_facet(facet_id: int, data: SFacetUpdate):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)
    if not facet:
        raise HTTPException(status_code=404, detail="Фацет не найден")

    updated = await FacetsDAO.update({"id": facet_id}, **data.model_dump())

    return updated


@router.delete("/facets/{facet_id}", status_code=204, summary="Удалить фацет",
        description="Удаляет фацет по id.")
async def delete_facet(facet_id: int):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)
    if not facet:
        raise HTTPException(status_code=404, detail="Фацет не найден")
    
    await FacetsDAO.delete_by(id=facet_id)


@router.post("/temperings", summary="Создать новую закалку", status_code=201,
        description="Добавляет закалку в базу. Используется в админ-панели.")
async def add_tempering(data: STemperingUpdate):
    tempering = await TemperingDAO.add_and_return(**data.model_dump())

    return tempering


@router.get("/temperings/{tempering_id}", response_model=STemperingOut, summary="Получить данные закалки",
        description="Возвращает данные закалки по id.")
async def get_tempering_data(tempering_id: int):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

    if not tempering:
        raise HTTPException(status_code=404, detail="Закалка не найдена")
    
    return tempering


@router.put("/temperings/{tempering_id}", response_model=STemperingOut, summary="Обновить закалку",
        description="Полное обновление данных закалки. Заменяет все существующие поля.")
async def update_tempering(tempering_id: int, data: STemperingUpdate):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)
    if not tempering:
        raise HTTPException(status_code=404, detail="Закалка не найдена")

    updated = await TemperingDAO.update({"id": tempering_id}, **data.model_dump())

    return updated


@router.delete("/temperings/{tempering_id}", status_code=204, summary="Удалить закалку",
        description="Удаляет закалку по id.")
async def delete_tempering(tempering_id: int):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)
    if not tempering:
        raise HTTPException(status_code=404, detail="Закалка не найдена")
    
    await TemperingDAO.delete_by(id=tempering_id)