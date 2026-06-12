from fastapi import APIRouter

from app.api.v1 import customers, database_lab, health, orders, products

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(database_lab.router, tags=["database-lab"])
api_router.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
api_router.include_router(products.router, prefix="/api/v1/products", tags=["products"])
api_router.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
