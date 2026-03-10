from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.admin.dependencies import user_is_admin
from app.admin.service import parse_categories_of_products, parse_products_by_names
from app.database import new_session
from app.products.dao import CategoriesDAO, EdgesDAO, FacetsDAO, ProductsDAO, TemperingDAO
from app.products.schemas import (
    SEdgeOut,
    SEdgeUpdate,
    SFacetOut,
    SFacetUpdate,
    STemperingOut,
    STemperingUpdate,
)


router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(user_is_admin)])


@router.post("/add_all_products")
async def add_all_products(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="РќСѓР¶РµРЅ .xlsx С„Р°Р№Р»")

    read_bytes = await file.read()
    categories = parse_categories_of_products(read_bytes)
    products = parse_products_by_names(read_bytes)

    async with new_session() as session:
        try:
            async with session.begin():
                for category in categories:
                    existing_category = await CategoriesDAO.find_one_or_none(
                        session=session,
                        category_name=category["category_name"],
                    )
                    if not existing_category:
                        await CategoriesDAO.add(session=session, category_name=category["category_name"])

                all_categories = await CategoriesDAO.get_all(session=session)
                category_name_to_id = {category.category_name: category.id for category in all_categories}

                await ProductsDAO.make_all_unactive(session=session)

                for product in products:
                    category_id = category_name_to_id[product["category_name"]]
                    product_data = product.copy()
                    product_data.pop("category_name")
                    product_data["category_id"] = category_id

                    existing_product = await ProductsDAO.find_one_or_none(
                        session=session,
                        name=product_data["name"],
                        category_id=category_id,
                    )

                    if existing_product is not None:
                        await ProductsDAO.update(
                            {"id": existing_product.id},
                            session=session,
                            **product_data,
                            is_active=True,
                        )
                    else:
                        await ProductsDAO.add(session=session, **product_data)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="РћС€РёР±РєР° СЃРµСЂРІРµСЂР°")

    return {"message": "Р’СЃРµ С‚РѕРІР°СЂС‹ СѓСЃРїРµС€РЅРѕ РґРѕР±Р°РІР»РµРЅС‹"}


@router.get("/edges", response_model=list[SEdgeOut])
async def get_edges():
    return await EdgesDAO.get_all()


@router.post("/edges", response_model=SEdgeOut, status_code=201)
async def add_edge(data: SEdgeUpdate):
    return await EdgesDAO.add_and_return(**data.model_dump())


@router.get("/edges/{edge_id}", response_model=SEdgeOut)
async def get_edge_data(edge_id: int):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)

    if not edge:
        raise HTTPException(status_code=404, detail="РћР±СЂР°Р±РѕС‚РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    return edge


@router.put("/edges/{edge_id}", response_model=SEdgeOut)
async def update_edge(edge_id: int, data: SEdgeUpdate):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)

    if not edge:
        raise HTTPException(status_code=404, detail="РћР±СЂР°Р±РѕС‚РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    return await EdgesDAO.update({"id": edge_id}, **data.model_dump())


@router.delete("/edges/{edge_id}", status_code=204)
async def delete_edge(edge_id: int):
    edge = await EdgesDAO.find_one_or_none(id=edge_id)

    if not edge:
        raise HTTPException(status_code=404, detail="РћР±СЂР°Р±РѕС‚РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    await EdgesDAO.delete_by(id=edge_id)


@router.get("/facets", response_model=list[SFacetOut])
async def get_facets():
    return await FacetsDAO.get_all()


@router.post("/facets", response_model=SFacetOut, status_code=201)
async def add_facet(data: SFacetUpdate):
    return await FacetsDAO.add_and_return(**data.model_dump())


@router.get("/facets/{facet_id}", response_model=SFacetOut)
async def get_facet_data(facet_id: int):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)

    if not facet:
        raise HTTPException(status_code=404, detail="Р¤Р°С†РµС‚ РЅРµ РЅР°Р№РґРµРЅ")

    return facet


@router.put("/facets/{facet_id}", response_model=SFacetOut)
async def update_facet(facet_id: int, data: SFacetUpdate):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)

    if not facet:
        raise HTTPException(status_code=404, detail="Р¤Р°С†РµС‚ РЅРµ РЅР°Р№РґРµРЅ")

    return await FacetsDAO.update({"id": facet_id}, **data.model_dump())


@router.delete("/facets/{facet_id}", status_code=204)
async def delete_facet(facet_id: int):
    facet = await FacetsDAO.find_one_or_none(id=facet_id)

    if not facet:
        raise HTTPException(status_code=404, detail="Р¤Р°С†РµС‚ РЅРµ РЅР°Р№РґРµРЅ")

    await FacetsDAO.delete_by(id=facet_id)


@router.get("/temperings", response_model=list[STemperingOut])
async def get_temperings():
    return await TemperingDAO.get_all()


@router.post("/temperings", response_model=STemperingOut, status_code=201)
async def add_tempering(data: STemperingUpdate):
    return await TemperingDAO.add_and_return(**data.model_dump())


@router.get("/temperings/{tempering_id}", response_model=STemperingOut)
async def get_tempering_data(tempering_id: int):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

    if not tempering:
        raise HTTPException(status_code=404, detail="Р—Р°РєР°Р»РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    return tempering


@router.put("/temperings/{tempering_id}", response_model=STemperingOut)
async def update_tempering(tempering_id: int, data: STemperingUpdate):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

    if not tempering:
        raise HTTPException(status_code=404, detail="Р—Р°РєР°Р»РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    return await TemperingDAO.update({"id": tempering_id}, **data.model_dump())


@router.delete("/temperings/{tempering_id}", status_code=204)
async def delete_tempering(tempering_id: int):
    tempering = await TemperingDAO.find_one_or_none(id=tempering_id)

    if not tempering:
        raise HTTPException(status_code=404, detail="Р—Р°РєР°Р»РєР° РЅРµ РЅР°Р№РґРµРЅР°")

    await TemperingDAO.delete_by(id=tempering_id)
