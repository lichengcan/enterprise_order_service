from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.product import ProductCreate, ProductRead
from app.services.products import ProductService

router = APIRouter()


@router.post("", response_model=ProductRead, status_code=201)
def create_product(payload: ProductCreate, session: DbSession) -> ProductRead:
    return ProductService(session).create_product(payload)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: DbSession) -> ProductRead:
    return ProductService(session).get_product(product_id)


@router.get("", response_model=list[ProductRead])
def list_products(session: DbSession, limit: int = 20, offset: int = 0) -> list[ProductRead]:
    return ProductService(session).list_products(limit=limit, offset=offset)

