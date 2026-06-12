# Database CRUD Examples

这里放的是独立数据库示例，方便你学习 Python 连接 MongoDB 和 MySQL 的增删查改。

这版按更接近企业项目的方式组织：

- 配置从 `.env` 读取，不把密码写死在代码里。
- 入口 `main()` 只编排演示流程。
- Repository 层集中封装数据库访问。
- Service 层负责业务流程和事务边界。
- MySQL 示例使用 SQLAlchemy ORM，避免业务代码里散落 SQL。
- MongoDB 示例使用 PyMongo，但集合操作集中在 Repository。

## 安装依赖

```powershell
cd D:\code\gitee\python\enterprise_order_service
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

## MongoDB CRUD

MongoDB 服务默认连接：

```text
mongodb://127.0.0.1:27017
```

运行：

```powershell
python -m examples.mongodb_crud
```

## MySQL CRUD

MySQL 连接信息来自 `.env`：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DATABASE=python_demo
```

如果你的 MySQL root 有密码，请先修改 `.env` 里的 `MYSQL_PASSWORD`。

真实企业项目里，建表和字段变更通常不用 `create_all()`，而是用 Alembic、Flyway 或 Liquibase 这类迁移工具。这里为了学习和直接运行，示例里保留了自动创建 demo 数据库和 demo 表的逻辑。

运行：

```powershell
python -m examples.mysql_crud
```
