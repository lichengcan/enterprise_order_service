# Security Best Practices Report

## Executive Summary

This FastAPI backend is a clean learning project, but it is not production-ready from a security baseline perspective. The largest gaps are missing authentication/authorization, publicly exposed predictable resource IDs, production documentation exposure, and missing request/rate limits. I did not find raw SQL injection sinks, command execution, unsafe file serving, redirects, SSRF, template rendering, cookie sessions, or WebSocket surfaces in the current code.

## High Severity

### SBP-001: No Authentication or Authorization on Business APIs

- Rule ID: FASTAPI-AUTH-001, FASTAPI-AUTHZ-001
- Severity: High
- Location:
  - `app/api/v1/customers.py:10-22`
  - `app/api/v1/products.py:10-22`
  - `app/api/v1/orders.py:10-31`
- Evidence:

```python
@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(payload: CustomerCreate, session: DbSession) -> CustomerRead:
    return CustomerService(session).create_customer(payload)
```

The same pattern appears on products and orders, with no `Depends(...)` or `Security(...)` dependency enforcing an authenticated user or role.

- Impact: Any caller who can reach the API can create customers, create products, create orders, list customers, list products, retrieve orders, and list another customer's orders.
- Fix: Add a centralized authentication dependency, then attach it to protected routers. Add role checks for product/customer administration and object-level ownership checks for customer/order reads.
- Mitigation: If this stays a local-only learning service, bind only to localhost and do not expose it publicly. For any shared environment, place it behind an authenticated gateway until app-level auth exists.
- False positive notes: If auth is enforced by an external API gateway, that is not visible in the repository and should be documented.

### SBP-002: Predictable Public IDs Enable Enumeration and IDOR

- Rule ID: FASTAPI-AUTHZ-001, General Security Advice: Avoid Incrementing IDs for Public IDs
- Severity: High
- Location:
  - `app/api/v1/customers.py:15-17`
  - `app/api/v1/products.py:15-17`
  - `app/api/v1/orders.py:15-31`
  - `app/schemas/order.py:29-38`
  - `app/schemas/customer.py:11-18`
  - `app/schemas/product.py:13-21`
- Evidence:

```python
@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, session: DbSession) -> OrderRead:
    return OrderService(session).get_order(order_id)
```

Response models return internal integer IDs, and path parameters accept integer IDs directly.

- Impact: Once deployed, attackers can enumerate `1`, `2`, `3`, etc. to discover customers, products, and orders. Combined with missing auth, this becomes direct data exposure.
- Fix: Add separate public IDs such as UUIDs or random tokens for external URLs. Keep database integer primary keys internal. Enforce object-level authorization before returning any resource.
- Mitigation: At minimum, do not expose list/read endpoints publicly until auth is added.
- False positive notes: Predictable IDs are less risky for purely public catalog data, but customers and orders are not purely public resources.

## Medium Severity

### SBP-003: OpenAPI and Interactive Docs Are Always Enabled

- Rule ID: FASTAPI-OPENAPI-001
- Severity: Medium
- Location: `app/main.py:23-29`
- Evidence:

```python
application = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
```

- Impact: In production, `/docs`, `/redoc`, and the default `/openapi.json` make endpoint discovery easier and reveal API shapes, DTOs, and business operations.
- Fix: Disable docs in `prod` using environment-gated settings, or protect docs with authentication or network allowlists.
- Mitigation: Restrict documentation routes at the reverse proxy or only expose them on internal networks.
- False positive notes: Exposed docs can be acceptable for public APIs if intentionally published and protected as needed.

### SBP-004: No Trusted Host Validation

- Rule ID: Production Baseline: Host header validation
- Severity: Medium
- Location: `app/main.py:20-39`
- Evidence: The application creates a `FastAPI` instance and includes routers, but does not add Starlette `TrustedHostMiddleware`.
- Impact: If deployed directly or behind a permissive proxy, forged `Host` headers may contribute to cache poisoning, incorrect absolute URL generation, routing confusion, and log/audit ambiguity.
- Fix: Add environment-driven `allowed_hosts` config and enable `TrustedHostMiddleware` in production.
- Mitigation: Enforce host validation at the reverse proxy or gateway and document that boundary.
- False positive notes: If an upstream proxy already rejects invalid hosts, app-level middleware is defense-in-depth rather than the primary control.

### SBP-005: Request Size, List Length, Quantity, and Rate Limits Are Missing

- Rule ID: FASTAPI-REQ-001
- Severity: Medium
- Location:
  - `app/schemas/order.py:8-15`
  - `app/api/v1/customers.py:20-22`
  - `app/api/v1/products.py:20-22`
  - `app/api/v1/orders.py:15-26`
- Evidence:

```python
class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(min_length=1)
```

`items` has no maximum length, `quantity` has no upper bound, and list endpoints accept raw `limit`/`offset` parameters without `Field` constraints at the API layer.

- Impact: Attackers can send very large orders or abusive pagination requests to consume CPU, memory, and database work. Large quantities can also stress integer handling and business validation.
- Fix: Add schema caps, for example `items: list[OrderItemCreate] = Field(min_length=1, max_length=100)` and `quantity: int = Field(gt=0, le=999)`. Use `Query(ge=1, le=100)` for pagination. Add rate limiting at gateway or middleware.
- Mitigation: Configure reverse proxy body-size limits and per-IP/user throttling.
- False positive notes: SQLite/local development hides much of the operational impact; this matters once the API is network-accessible.

### SBP-006: Inventory Deduction Is Race-Prone

- Rule ID: Business integrity / authorization-adjacent abuse risk
- Severity: Medium
- Location: `app/services/orders.py:42-73`
- Evidence:

```python
if product.stock < quantity:
    raise BusinessError(...)

product.stock -= quantity
...
self.session.commit()
```

- Impact: Concurrent requests can both observe sufficient stock before either commits, causing overselling or inconsistent inventory. A malicious or impatient client can amplify this by sending parallel order requests.
- Fix: Use database-level atomic updates or row locks where supported, such as `UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty`, then verify affected row count inside the same transaction.
- Mitigation: For SQLite learning mode, document the limitation. For production, use PostgreSQL/MySQL with proper transaction isolation and tests for concurrent ordering.
- False positive notes: This is primarily business integrity rather than classic OWASP injection, but it is a real enterprise backend risk.

## Low Severity

### SBP-007: Write Schemas Do Not Explicitly Reject Extra Fields

- Rule ID: FASTAPI-VALID-001
- Severity: Low
- Location:
  - `app/schemas/customer.py:6-8`
  - `app/schemas/product.py:6-10`
  - `app/schemas/order.py:8-15`
- Evidence: The request models do not set `model_config = ConfigDict(extra="forbid")`.
- Impact: Pydantic v2 ignores unexpected fields by default. The current code maps fields explicitly, so this is not an immediate mass-assignment bug, but rejecting unknown fields gives clients clearer errors and prevents future accidental overposting bugs.
- Fix: Add a shared strict base schema for write models or set `ConfigDict(extra="forbid")` on create/update DTOs.
- Mitigation: Continue avoiding direct `Model(**payload.model_dump())` writes into ORM objects for privileged fields.
- False positive notes: This becomes more important when update endpoints are added.

### SBP-008: Dependencies Are Range-Based Without a Lock File

- Rule ID: FASTAPI-SUPPLY-001
- Severity: Low
- Location: `pyproject.toml:6-20`
- Evidence:

```toml
"fastapi>=0.111.0",
"uvicorn[standard]>=0.30.0",
"sqlalchemy>=2.0.30",
```

- Impact: Builds are not reproducible. A future dependency release can change behavior or introduce a regression, while a stale local environment can miss security fixes.
- Fix: For applications, add a lock workflow such as `uv.lock`, `requirements.lock`, Poetry lock, or pip-tools. Regularly audit and update FastAPI, Starlette, Uvicorn, Pydantic, and SQLAlchemy.
- Mitigation: Pin exact versions in deployment artifacts even if development keeps broad ranges.
- False positive notes: Range constraints are common for libraries; applications benefit more from lock files.

## Positive Findings

- SQL access uses SQLAlchemy ORM/select APIs; no raw SQL string concatenation was found.
- No command execution sinks such as `subprocess`, `os.system`, or `shell=True` were found.
- No file upload/download, `StaticFiles`, `FileResponse`, SSRF-style outbound fetch, redirects, template rendering, cookie sessions, or WebSocket endpoints were found.
- API routes use explicit `response_model` declarations, reducing accidental excessive data exposure.
- The app does not enable `FastAPI(debug=True)`.

