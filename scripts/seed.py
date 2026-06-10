from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.product import Product


def main() -> None:
    init_db()
    with SessionLocal() as session:
        if not session.query(Customer).first():
            session.add_all(
                [
                    Customer(email="alice@example.com", name="Alice"),
                    Customer(email="bob@example.com", name="Bob"),
                ]
            )

        if not session.query(Product).first():
            session.add_all(
                [
                    Product(sku="BOOK-PY-001", name="Effective Python", price_cents=6999, stock=20),
                    Product(sku="KEYBOARD-001", name="Mechanical Keyboard", price_cents=15900, stock=8),
                    Product(sku="MOUSE-001", name="Wireless Mouse", price_cents=7990, stock=15),
                ]
            )

        session.commit()
    print("Seed data is ready.")


if __name__ == "__main__":
    main()

