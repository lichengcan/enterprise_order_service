from datetime import datetime
from functools import lru_cache
from os import getenv
from re import fullmatch

from dotenv import load_dotenv
from sqlalchemy import BigInteger, DateTime, Integer, String, create_engine, func, select, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.demo_db.schemas import DemoUserCreate, DemoUserRead

load_dotenv()


class MySQLDemoError(RuntimeError):
    pass


class MySQLBase(DeclarativeBase):
    pass


class MySQLDemoUser(MySQLBase):
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


def _safe_identifier(name: str) -> str:
    if not fullmatch(r"[A-Za-z0-9_]+", name):
        raise MySQLDemoError(f"Unsafe MySQL database name: {name!r}")
    return name


def _database_name() -> str:
    return _safe_identifier(getenv("MYSQL_DATABASE", "python_demo"))


def _mysql_url(include_database: bool) -> URL:
    return URL.create(
        "mysql+mysqlconnector",
        username=getenv("MYSQL_USER", "root"),
        password=getenv("MYSQL_PASSWORD", ""),
        host=getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(getenv("MYSQL_PORT", "3306")),
        database=_database_name() if include_database else None,
    )


@lru_cache
def get_mysql_engine() -> Engine:
    return create_engine(_mysql_url(include_database=True), pool_pre_ping=True)


@lru_cache
def get_mysql_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_mysql_engine(), autoflush=False, expire_on_commit=False)


def ensure_mysql_schema() -> None:
    admin_engine = create_engine(_mysql_url(include_database=False), pool_pre_ping=True)
    with admin_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{_database_name()}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )

    MySQLBase.metadata.create_all(bind=get_mysql_engine())


class MySQLDemoUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: MySQLDemoUser) -> MySQLDemoUser:
        self.session.add(user)
        self.session.flush()
        return user

    def get(self, user_id: int) -> MySQLDemoUser | None:
        return self.session.get(MySQLDemoUser, user_id)

    def list(self, limit: int) -> list[MySQLDemoUser]:
        statement = select(MySQLDemoUser).order_by(MySQLDemoUser.id.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def delete(self, user: MySQLDemoUser) -> None:
        self.session.delete(user)


class MySQLDemoUserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = MySQLDemoUserRepository(session)

    def create_user(self, payload: DemoUserCreate) -> DemoUserRead:
        user = MySQLDemoUser(name=payload.name, email=str(payload.email), age=payload.age)
        self.users.add(user)
        self.session.commit()
        self.session.refresh(user)
        return _to_read(user)

    def get_user(self, user_id: str) -> DemoUserRead | None:
        user = self.users.get(_parse_id(user_id))
        return _to_read(user) if user else None

    def list_users(self, limit: int) -> list[DemoUserRead]:
        return [_to_read(user) for user in self.users.list(limit=limit)]

    def update_user_email(self, user_id: str, email: str) -> bool:
        user = self.users.get(_parse_id(user_id))
        if not user:
            return False

        user.email = email
        self.session.commit()
        return True

    def delete_user(self, user_id: str) -> bool:
        user = self.users.get(_parse_id(user_id))
        if not user:
            return False

        self.users.delete(user)
        self.session.commit()
        return True


def _parse_id(user_id: str) -> int:
    try:
        return int(user_id)
    except ValueError as exc:
        raise MySQLDemoError("MySQL user id must be an integer") from exc


def _to_read(user: MySQLDemoUser) -> DemoUserRead:
    return DemoUserRead(
        id=str(user.id),
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
