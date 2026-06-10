from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models.customer import Customer
from app.repositories.customers import CustomerRepository
from app.schemas.customer import CustomerCreate


class CustomerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)

    def create_customer(self, payload: CustomerCreate) -> Customer:
        existing = self.customers.get_by_email(payload.email)
        if existing:
            raise BusinessError("CUSTOMER_EMAIL_EXISTS", "Customer email already exists")

        customer = Customer(email=str(payload.email), name=payload.name)
        self.customers.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def get_customer(self, customer_id: int) -> Customer:
        customer = self.customers.get(customer_id)
        if not customer:
            raise NotFoundError("Customer", customer_id)
        return customer

    def list_customers(self, limit: int, offset: int) -> list[Customer]:
        return self.customers.list(limit=limit, offset=offset)

