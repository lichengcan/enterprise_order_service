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
    """订单业务服务。

    Service 层负责组织业务规则和事务流程，类似 Java 项目里的
    OrderService / OrderServiceImpl。这里不直接处理 HTTP，也不直接
    拼 SQL，而是调用 Repository 完成数据访问。
    """

    def __init__(self, session: Session) -> None:
        """创建订单服务对象。

        参数类型写法说明：
        - `session: Session` 表示 session 参数应该是 SQLAlchemy 的 Session。
        - `-> None` 表示这个构造方法不返回业务对象。
        """
        self.session = session
        self.customers = CustomerRepository(session)
        self.products = ProductRepository(session)
        self.orders = OrderRepository(session)

    def create_order(self, payload: OrderCreate) -> Order:
        """创建订单。

        `payload: OrderCreate` 是入参类型，表示调用方需要传订单创建 DTO。
        `-> Order` 是返回值类型，表示方法成功后返回 ORM 订单对象。
        """
        # 1. 校验客户存在且可用。业务异常会被 FastAPI 全局异常处理器转成 JSON 响应。
        customer = self.customers.get(payload.customer_id)
        if not customer:
            raise NotFoundError("Customer", payload.customer_id)
        if not customer.is_active:
            raise BusinessError("CUSTOMER_DISABLED", "Customer is disabled")

        # 2. 合并重复商品项。defaultdict(int) 会给不存在的 key 默认值 0。
        #    例如同一个商品在请求里出现两次，这里会把数量累加成一条。
        quantities: dict[int, int] = defaultdict(int)
        for item in payload.items:
            quantities[item.product_id] += item.quantity

        # 3. 一次性查询所有商品，再转成 dict，避免在循环里反复查数据库。
        products = self.products.get_many(list(quantities.keys()))
        products_by_id = {product.id: product for product in products}

        # 4. 找出请求里存在、但数据库里不存在的商品 id。
        missing_ids = sorted(set(quantities) - set(products_by_id))
        if missing_ids:
            raise BusinessError("PRODUCT_NOT_FOUND", f"Product ids do not exist: {missing_ids}", 404)

        total_cents = 0
        order_items: list[OrderItem] = []

        # 5. 校验库存、计算金额、扣减库存，并生成订单明细。
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

            # 保存商品快照：即使未来商品改名或改价，历史订单仍保持下单时的信息。
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

        # 6. 组装订单主表对象。此时还没有真正写入数据库。
        order = Order(
            order_no=self._new_order_no(),
            customer_id=customer.id,
            status=OrderStatus.CREATED,
            total_cents=total_cents,
            items=order_items,
        )
        # 7. add + commit 才会提交事务；refresh 用数据库里的最终值刷新对象。
        self.orders.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def get_order(self, order_id: int) -> Order:
        """按订单 id 查询订单。

        `order_id: int` 表示参数必须是整数。
        `-> Order` 表示如果找到，就返回订单对象；找不到则抛 NotFoundError。
        """
        order = self.orders.get(order_id)
        if not order:
            raise NotFoundError("Order", order_id)
        return order

    def list_customer_orders(self, customer_id: int, limit: int, offset: int) -> list[Order]:
        """查询某个客户的订单列表。

        `-> list[Order]` 表示返回 Order 对象列表。
        `list[Order]` 是 Python 3.9+ 的泛型写法，类似 Java 的 `List<Order>`。
        """
        customer = self.customers.get(customer_id)
        if not customer:
            raise NotFoundError("Customer", customer_id)
        return self.orders.list_by_customer(customer_id=customer_id, limit=limit, offset=offset)

    @staticmethod
    def _new_order_no() -> str:
        """生成订单号。

        `@staticmethod` 表示这个方法不依赖 self，可以理解成 Java 里的静态方法。
        `-> str` 表示返回字符串。
        """
        return f"ORD-{uuid4().hex[:12].upper()}"
