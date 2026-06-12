from datetime import datetime, timezone
from functools import lru_cache
from os import getenv
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from app.demo_db.schemas import DemoUserCreate, DemoUserRead

load_dotenv()


class MongoDemoError(RuntimeError):
    pass


@lru_cache
def get_mongo_client() -> MongoClient[dict[str, Any]]:
    client: MongoClient[dict[str, Any]] = MongoClient(
        getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=3000,
    )
    client.admin.command("ping")
    return client


def get_mongo_users_collection() -> Collection[dict[str, Any]]:
    database_name = getenv("MONGODB_DATABASE", "python_demo")
    return get_mongo_client()[database_name]["demo_users"]


def ensure_mongo_schema() -> None:
    get_mongo_users_collection().create_index([("email", ASCENDING)], unique=True)


class MongoDemoUserRepository:
    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        self.collection = collection

    def add(self, payload: DemoUserCreate) -> str:
        now = datetime.now(timezone.utc)
        result = self.collection.insert_one(
            {
                "name": payload.name,
                "email": str(payload.email),
                "age": payload.age,
                "created_at": now,
                "updated_at": now,
            }
        )
        return str(result.inserted_id)

    def get(self, user_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": _object_id(user_id)})

    def list(self, limit: int) -> list[dict[str, Any]]:
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        return list(cursor)

    def update_email(self, user_id: str, email: str) -> bool:
        result = self.collection.update_one(
            {"_id": _object_id(user_id)},
            {"$set": {"email": email, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count == 1

    def delete(self, user_id: str) -> bool:
        result = self.collection.delete_one({"_id": _object_id(user_id)})
        return result.deleted_count == 1


class MongoDemoUserService:
    def __init__(self, users: MongoDemoUserRepository) -> None:
        self.users = users

    def create_user(self, payload: DemoUserCreate) -> DemoUserRead:
        user_id = self.users.add(payload)
        user = self.users.get(user_id)
        if not user:
            raise MongoDemoError("MongoDB user was created but could not be loaded")
        return _to_read(user)

    def get_user(self, user_id: str) -> DemoUserRead | None:
        user = self.users.get(user_id)
        return _to_read(user) if user else None

    def list_users(self, limit: int) -> list[DemoUserRead]:
        return [_to_read(user) for user in self.users.list(limit=limit)]

    def update_user_email(self, user_id: str, email: str) -> bool:
        return self.users.update_email(user_id, email)

    def delete_user(self, user_id: str) -> bool:
        return self.users.delete(user_id)


def create_mongo_user_service() -> MongoDemoUserService:
    return MongoDemoUserService(MongoDemoUserRepository(get_mongo_users_collection()))


def _object_id(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except InvalidId as exc:
        raise MongoDemoError("MongoDB user id must be a valid ObjectId") from exc


def _to_read(document: dict[str, Any]) -> DemoUserRead:
    return DemoUserRead(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        age=document["age"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )

