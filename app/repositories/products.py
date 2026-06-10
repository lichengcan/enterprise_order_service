from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, product: Product) -> Product:
        self.session.add(product)
        self.session.flush()
        return product

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def get_many(self, product_ids: list[int]) -> list[Product]:
        if not product_ids:
            return []
        statement = select(Product).where(Product.id.in_(product_ids))
        return list(self.session.scalars(statement).all())

    def get_by_sku(self, sku: str) -> Product | None:
        return self.session.scalar(select(Product).where(Product.sku == sku))

    def list(self, limit: int, offset: int) -> list[Product]:
        statement = select(Product).order_by(Product.id).limit(limit).offset(offset)
        return list(self.session.scalars(statement).all())

