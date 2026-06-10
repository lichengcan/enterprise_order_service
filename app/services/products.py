from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models.product import Product
from app.repositories.products import ProductRepository
from app.schemas.product import ProductCreate


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)

    def create_product(self, payload: ProductCreate) -> Product:
        existing = self.products.get_by_sku(payload.sku)
        if existing:
            raise BusinessError("PRODUCT_SKU_EXISTS", "Product SKU already exists")

        product = Product(
            sku=payload.sku,
            name=payload.name,
            price_cents=payload.price_cents,
            stock=payload.stock,
        )
        self.products.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def get_product(self, product_id: int) -> Product:
        product = self.products.get(product_id)
        if not product:
            raise NotFoundError("Product", product_id)
        return product

    def list_products(self, limit: int, offset: int) -> list[Product]:
        return self.products.list(limit=limit, offset=offset)

