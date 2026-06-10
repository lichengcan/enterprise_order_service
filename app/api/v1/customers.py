from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.customer import CustomerCreate, CustomerRead
from app.services.customers import CustomerService

router = APIRouter()


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(payload: CustomerCreate, session: DbSession) -> CustomerRead:
    return CustomerService(session).create_customer(payload)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, session: DbSession) -> CustomerRead:
    return CustomerService(session).get_customer(customer_id)


@router.get("", response_model=list[CustomerRead])
def list_customers(session: DbSession, limit: int = 20, offset: int = 0) -> list[CustomerRead]:
    return CustomerService(session).list_customers(limit=limit, offset=offset)

