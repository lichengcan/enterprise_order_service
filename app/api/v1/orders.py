from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.order import OrderCreate, OrderRead
from app.services.orders import OrderService

router = APIRouter()


@router.post("", response_model=OrderRead, status_code=201)
def create_order(payload: OrderCreate, session: DbSession) -> OrderRead:
    return OrderService(session).create_order(payload)


@router.get("/by-customer/{customer_id}", response_model=list[OrderRead])
def list_customer_orders(
    customer_id: int,
    session: DbSession,
    limit: int = 20,
    offset: int = 0,
) -> list[OrderRead]:
    return OrderService(session).list_customer_orders(
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, session: DbSession) -> OrderRead:
    return OrderService(session).get_order(order_id)
