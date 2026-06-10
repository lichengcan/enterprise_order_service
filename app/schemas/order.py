from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(BaseModel):
    product_id: int
    sku_snapshot: str
    product_name_snapshot: str
    unit_price_cents: int
    quantity: int
    subtotal_cents: int

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    order_no: str
    customer_id: int
    status: OrderStatus
    total_cents: int
    items: list[OrderItemRead]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

