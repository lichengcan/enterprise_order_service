from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    price_cents: int = Field(gt=0)
    stock: int = Field(ge=0)


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    price_cents: int
    stock: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

