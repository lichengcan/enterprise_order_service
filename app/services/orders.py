from collections import defaultdict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models.order import Order, OrderItem, OrderStatus
from app.repositories.customers import CustomerRepository
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.schemas.order import OrderCreate


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)

    def create_order(self, payload: OrderCreate) -> Order:
        customer = self.customers.get(payload.customer_id)
        if not customer:
            raise NotFoundError("Customer", payload.customer_id)
        if not customer.is_active:
            raise BusinessError("CUSTOMER_DISABLED", "Customer is disabled")

        quantities: dict[int, int] = defaultdict(int)
        for item in payload.items:
            quantities[item.product_id] += item.quantity

        products = self.products.get_many(list(quantities.keys()))
        products_by_id = {product.id: product for product in products}

        missing_ids = sorted(set(quantities) - set(products_by_id))
        if missing_ids:
            raise BusinessError("PRODUCT_NOT_FOUND", f"Product ids do not exist: {missing_ids}", 404)

        total_cents = 0
        order_items: list[OrderItem] = []

        for product_id, quantity in quantities.items():
            product = products_by_id[product_id]
            if product.stock < quantity:
                raise BusinessError(
                    "INSUFFICIENT_STOCK",
                    f"Product {product.sku} only has {product.stock} items in stock",
                )

            subtotal = product.price_cents * quantity
            total_cents += subtotal
            product.stock -= quantity

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    sku_snapshot=product.sku,
                    product_name_snapshot=product.name,
                    unit_price_cents=product.price_cents,
                    quantity=quantity,
                    subtotal_cents=subtotal,
                )
            )

        order = Order(
            order_no=self._new_order_no(),
            customer_id=customer.id,
            status=OrderStatus.CREATED,
            total_cents=total_cents,
            items=order_items,
        )
        self.orders.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def get_order(self, order_id: int) -> Order:
        order = self.orders.get(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        return order

    def list_customer_orders(self, customer_id: int, limit: int, offset: int) -> list[Order]:
        customer = self.customers.get(customer_id)
        if not customer:
            raise NotFoundError("Customer", customer_id)
        return self.orders.list_by_customer(customer_id=customer_id, limit=limit, offset=offset)

    @staticmethod
    def _new_order_no() -> str:
        return f"ORD-{uuid4().hex[:12].upper()}"
