from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        self.session.flush()
        return customer

    def get(self, customer_id: int) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        return self.session.scalar(select(Customer).where(Customer.email == email))

    def list(self, limit: int, offset: int) -> list[Customer]:
        statement = select(Customer).order_by(Customer.id).limit(limit).offset(offset)
        return list(self.session.scalars(statement).all())

if __name__ == "__main__":
    # 用 SQLite 内存数据库测试，不会影响真实数据
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.base import Base
    from app.models.order import Order  # noqa: F401  确保关系映射注册
    from app.models.product import Product  # noqa: F401

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)  # 自动建表

    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        repo = CustomerRepository(session)

        # 测试新增
        customer = Customer(email="程灿test@example.com", name="张三1")
        saved = repo.add(customer)
        session.commit()
        print(f"新增成功: id={saved.id}, name={saved.name}, email={saved.email}")

        # 测试按ID查询
        found = repo.get(saved.id)
        print(f"按ID查询: {found.name}, {found.email}")

        # 测试按邮箱查询
        by_email = repo.get_by_email("test@example.com")
        if by_email:
            print(f"按邮箱查询: {by_email.name}, {by_email.email}")
        else:
            print("按邮箱查询: 未找到")

        # 测试列表查询
        repo.add(Customer(email="user2@example.com", name="李四"))
        session.commit()
        customers = repo.list(limit=10, offset=0)
        print(f"列表查询: 共 {len(customers)} 条记录")
        for c in customers:
            print(f"  - {c.id}: {c.name} ({c.email})")