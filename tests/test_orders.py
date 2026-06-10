from fastapi.testclient import TestClient


def test_create_order_deducts_stock_and_keeps_price_snapshot(client: TestClient) -> None:
    customer = client.post(
        "/api/v1/customers",
        json={"email": "alice@example.com", "name": "Alice"},
    ).json()
    product = client.post(
        "/api/v1/products",
        json={"sku": "BOOK-PY-001", "name": "Effective Python", "price_cents": 6999, "stock": 10},
    ).json()

    response = client.post(
        "/api/v1/orders",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "quantity": 2}]},
    )

    assert response.status_code == 201
    order = response.json()
    assert order["total_cents"] == 13998
    assert order["items"][0]["unit_price_cents"] == 6999
    assert order["items"][0]["quantity"] == 2

    product_after_order = client.get(f"/api/v1/products/{product['id']}").json()
    assert product_after_order["stock"] == 8


def test_create_order_rejects_insufficient_stock(client: TestClient) -> None:
    customer = client.post(
        "/api/v1/customers",
        json={"email": "bob@example.com", "name": "Bob"},
    ).json()
    product = client.post(
        "/api/v1/products",
        json={"sku": "MOUSE-001", "name": "Wireless Mouse", "price_cents": 7990, "stock": 1},
    ).json()

    response = client.post(
        "/api/v1/orders",
        json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "quantity": 2}]},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INSUFFICIENT_STOCK"

