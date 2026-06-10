# Enterprise Order Service

这是一个给 Java 转 Python 的学习项目。它不是“几个脚本拼一拼”的示例，而是按企业后端常见方式组织的 FastAPI 项目。

## 你会看到什么

- `api`: 类似 Java 的 Controller 层，处理 HTTP 入参和响应。
- `services`: 类似 Service 层，放业务规则和事务边界。
- `repositories`: 类似 DAO/Repository 层，封装数据库查询。
- `models`: SQLAlchemy ORM 实体，类似 JPA Entity。
- `schemas`: Pydantic DTO，类似 request/response DTO。
- `core`: 配置、日志、异常。
- `tests`: API 级别测试，使用内存 SQLite。

## 业务场景

一个简化的订单系统：

- 创建客户
- 创建商品
- 查询商品
- 创建订单
- 查询订单

创建订单时会校验：

- 客户存在且启用
- 商品存在
- 商品库存足够
- 订单项数量必须大于 0
- 下单后扣减库存
- 订单保存商品下单时的价格快照

## 快速启动

```bash
cd enterprise_order_service
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
python -m scripts.seed
uvicorn app.main:app --reload
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

## 运行测试

```bash
pytest
```

## Java 到 Python 对照

| Java / Spring 常见概念 | 这个项目里的 Python 写法 |
| --- | --- |
| `@RestController` | `fastapi.APIRouter` |
| `@Service` | `services/*.py` 中的普通类 |
| `@Repository` / DAO | `repositories/*.py` |
| JPA Entity | `models/*.py` SQLAlchemy ORM |
| DTO / VO | `schemas/*.py` Pydantic Model |
| `application.yml` | `.env` + `pydantic-settings` |
| DI 注入 | FastAPI `Depends` |
| 单元/集成测试 | `pytest` + `TestClient` |

## 推荐阅读顺序

1. [app/main.py](app/main.py): 应用入口。
2. [app/api/v1/orders.py](app/api/v1/orders.py): Controller 层。
3. [app/services/orders.py](app/services/orders.py): 订单业务规则。
4. [app/repositories/orders.py](app/repositories/orders.py): 数据访问。
5. [app/models/order.py](app/models/order.py): ORM 映射。
6. [tests/test_orders.py](tests/test_orders.py): 用测试理解完整链路。

