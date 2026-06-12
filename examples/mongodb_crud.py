from dataclasses import dataclass
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from pprint import pprint
from typing import Any
from uuid import uuid4

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class MongoSettings:
    """MongoDB 连接配置。"""

    uri: str
    database: str

    @classmethod
    def from_env(cls) -> "MongoSettings":
        return cls(
            uri=getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
            database=getenv("MONGODB_DATABASE", "python_demo"),
        )


@dataclass(frozen=True)
class UserCreate:
    """创建用户的入参 DTO。"""

    name: str
    email: str
    age: int


@dataclass(frozen=True)
class UserRead:
    """返回给调用方的用户 DTO。"""

    id: str
    name: str
    email: str
    age: int
    created_at: datetime
    updated_at: datetime


class MongoClientFactory:
    """集中创建 MongoDB Client。

    企业项目里一般会把客户端作为应用级单例，在应用关闭时统一 close。
    """

    def __init__(self, settings: MongoSettings) -> None:
        self.settings = settings

    def create(self) -> MongoClient[dict[str, Any]]:
        client: MongoClient[dict[str, Any]] = MongoClient(
            self.settings.uri,
            serverSelectionTimeoutMS=3000,
        )
        client.admin.command("ping")
        return client


class MongoUserRepository:
    """Repository 层：集中封装 MongoDB 集合操作。"""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self.collection = collection

    def ensure_indexes(self) -> None:
        self.collection.create_index([("email", ASCENDING)], unique=True)

    def add(self, payload: UserCreate) -> str:
        now = datetime.now(timezone.utc)
        result = self.collection.insert_one(
            {
                "name": payload.name,
                "email": payload.email,
                "age": payload.age,
                "created_at": now,
                "updated_at": now,
            }
        )
        return str(result.inserted_id)

    def get(self, user_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": ObjectId(user_id)})

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        return list(cursor)

    def update_email(self, user_id: str, email: str) -> bool:
        result = self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"email": email, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count == 1

    def delete(self, user_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count == 1


class MongoUserService:
    """Service 层：负责业务流程，屏蔽 MongoDB document 细节。"""

    def __init__(self, users: MongoUserRepository) -> None:
        self.users = users

    def create_user(self, payload: UserCreate) -> UserRead:
        user_id = self.users.add(payload)
        user = self.users.get(user_id)
        if not user:
            raise RuntimeError("User was created but could not be loaded")
        return to_user_read(user)

    def get_user(self, user_id: str) -> UserRead | None:
        user = self.users.get(user_id)
        return to_user_read(user) if user else None

    def list_users(self, limit: int = 20) -> list[UserRead]:
        return [to_user_read(user) for user in self.users.list(limit=limit)]

    def update_user_email(self, user_id: str, email: str) -> bool:
        return self.users.update_email(user_id, email)

    def delete_user(self, user_id: str) -> bool:
        return self.users.delete(user_id)


def to_user_read(document: dict[str, Any]) -> UserRead:
    return UserRead(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        age=document["age"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def main() -> None:
    settings = MongoSettings.from_env()
    client: MongoClient[dict[str, Any]] | None = None

    try:
        client = MongoClientFactory(settings).create()
        collection = client[settings.database]["demo_users"]

        repository = MongoUserRepository(collection)
        repository.ensure_indexes()
        service = MongoUserService(repository)
        suffix = uuid4().hex[:8]

        print("1. create")
        created = service.create_user(
            UserCreate(name="Alice", email=f"alice.{suffix}@example.com", age=28)
        )
        pprint(created)

        print("\n2. read")
        pprint(service.get_user(created.id))

        print("\n3. update")
        print("updated:", service.update_user_email(created.id, f"alice.new.{suffix}@example.com"))
        pprint(service.get_user(created.id))

        print("\n4. list")
        pprint(service.list_users(limit=5))

        print("\n5. delete")
        print("deleted:", service.delete_user(created.id))
        pprint(service.get_user(created.id))
    except DuplicateKeyError as exc:
        print("MongoDB 写入失败：email 唯一索引冲突。")
        print(f"原始错误: {exc}")
    except PyMongoError as exc:
        print("MongoDB 连接或执行失败。")
        print("请检查 .env 里的 MONGODB_URI / MONGODB_DATABASE。")
        print(f"原始错误: {exc}")
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
