from dataclasses import dataclass
from datetime import datetime
from os import getenv
from pathlib import Path
from pprint import pprint
from re import fullmatch
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import BigInteger, DateTime, Integer, String, create_engine, func, select, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class MySQLSettings:
    """MySQL 连接配置。

    企业项目里通常不会在代码里写死账号密码，而是从环境变量、配置中心、
    Kubernetes Secret 或云厂商 Secret Manager 读取。
    """

    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "MySQLSettings":
        return cls(
            host=getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(getenv("MYSQL_PORT", "3306")),
            user=getenv("MYSQL_USER", "root"),
            password=getenv("MYSQL_PASSWORD", ""),
            database=safe_identifier(getenv("MYSQL_DATABASE", "python_demo")),
        )


@dataclass(frozen=True)
class UserCreate:
    """创建用户的入参 DTO，类似 Java 里的 CreateUserRequest。"""

    name: str
    email: str
    age: int


@dataclass(frozen=True)
class UserRead:
    """返回给调用方的用户 DTO，避免直接暴露 ORM 对象。"""

    id: int
    name: str
    email: str
    age: int
    created_at: datetime
    updated_at: datetime


class Base(DeclarativeBase):
    pass


class DemoUser(Base):
    """MySQL 用户表 ORM 模型，类似 Java 里的 JPA Entity。"""

    __tablename__ = "demo_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def safe_identifier(name: str) -> str:
    """校验 MySQL 库名。

    SQL 参数占位符只能绑定值，不能绑定库名、表名这类标识符。
    所以标识符必须走白名单校验。
    """
    if not fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"Unsafe MySQL identifier: {name!r}")
    return name


def build_url(settings: MySQLSettings, include_database: bool) -> URL:
    return URL.create(
        "mysql+mysqlconnector",
        username=settings.user,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database if include_database else None,
    )


def create_mysql_engine(settings: MySQLSettings, include_database: bool = True) -> Engine:
    return create_engine(
        build_url(settings, include_database=include_database),
        pool_pre_ping=True,
        echo=False,
    )


def ensure_schema(settings: MySQLSettings) -> None:
    """准备数据库和表。

    真实企业项目通常使用 Alembic/Flyway/Liquibase 管理迁移。
    这里为了让示例可直接运行，保留一个轻量初始化函数。
    """
    admin_engine = create_mysql_engine(settings, include_database=False)
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )

    app_engine = create_mysql_engine(settings)
    Base.metadata.create_all(bind=app_engine)


class MySQLUserRepository:
    """Repository 层：集中封装数据库访问。

    Service 不直接写 SQL，也不关心 ORM 查询细节。
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: DemoUser) -> DemoUser:
        self.session.add(user)
        self.session.flush()
        return user

    def get(self, user_id: int) -> DemoUser | None:
        return self.session.get(DemoUser, user_id)

    def list(self, limit: int = 20) -> list[DemoUser]:
        statement = select(DemoUser).order_by(DemoUser.id.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def delete(self, user: DemoUser) -> None:
        self.session.delete(user)


class MySQLUserService:
    """Service 层：负责业务流程和事务边界。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = MySQLUserRepository(session)

    def create_user(self, payload: UserCreate) -> UserRead:
        user = DemoUser(name=payload.name, email=payload.email, age=payload.age)
        self.users.add(user)
        self.session.commit()
        self.session.refresh(user)
        return to_user_read(user)

    def get_user(self, user_id: int) -> UserRead | None:
        user = self.users.get(user_id)
        return to_user_read(user) if user else None

    def list_users(self, limit: int = 20) -> list[UserRead]:
        return [to_user_read(user) for user in self.users.list(limit=limit)]

    def update_user_email(self, user_id: int, email: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False

        user.email = email
        self.session.commit()
        return True

    def delete_user(self, user_id: int) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False

        self.users.delete(user)
        self.session.commit()
        return True


def to_user_read(user: DemoUser) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def main() -> None:
    settings = MySQLSettings.from_env()

    try:
        ensure_schema(settings)
        engine = create_mysql_engine(settings)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

        with SessionLocal() as session:
            service = MySQLUserService(session)
            suffix = uuid4().hex[:8]

            print("1. create")
            created = service.create_user(
                UserCreate(name="Bob", email=f"bob.{suffix}@example.com", age=30)
            )
            pprint(created)

            print("\n2. read")
            pprint(service.get_user(created.id))

            print("\n3. update")
            print("updated:", service.update_user_email(created.id, f"bob.new.{suffix}@example.com"))
            pprint(service.get_user(created.id))

            print("\n4. list")
            pprint(service.list_users(limit=5))

            print("\n5. delete")
            print("deleted:", service.delete_user(created.id))
            pprint(service.get_user(created.id))
    except SQLAlchemyError as exc:
        print("MySQL 连接或执行失败。")
        print("请检查 .env 里的 MYSQL_USER / MYSQL_PASSWORD / MYSQL_HOST / MYSQL_PORT。")
        if not settings.password:
            print("当前 MYSQL_PASSWORD 为空，所以驱动是用无密码方式连接的。")
        print(f"原始错误: {exc}")


if __name__ == "__main__":
    main()
