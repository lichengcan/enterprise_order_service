from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from json import dumps, loads
from os import getenv
from warnings import filterwarnings
from uuid import uuid4

from dotenv import load_dotenv
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.demo_db.schemas import (
    MilvusSearchHit,
    MilvusSearchRequest,
    MilvusVectorCreate,
    MilvusVectorRead,
    MilvusVectorUpdate,
)

load_dotenv()
filterwarnings("ignore", message=".*ORM-style PyMilvus API.*")

MILVUS_ALIAS = "database_lab_milvus"


class MilvusDemoError(RuntimeError):
    pass


def _collection_name() -> str:
    return getenv("MILVUS_COLLECTION", "python_demo_vectors")


def _dimension() -> int:
    return int(getenv("MILVUS_DIMENSION", "4"))


@lru_cache
def connect_milvus() -> bool:
    connections.connect(
        alias=MILVUS_ALIAS,
        host=getenv("MILVUS_HOST", "127.0.0.1"),
        port=getenv("MILVUS_PORT", "19530"),
    )
    return True


def ensure_milvus_schema() -> Collection:
    connect_milvus()
    name = _collection_name()

    if not utility.has_collection(name, using=MILVUS_ALIAS):
        schema = CollectionSchema(
            fields=[
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    is_primary=True,
                    max_length=64,
                ),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="payload_json", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=_dimension()),
                FieldSchema(name="created_at_ms", dtype=DataType.INT64),
                FieldSchema(name="updated_at_ms", dtype=DataType.INT64),
            ],
            description="Database Lab vector CRUD collection",
        )
        collection = Collection(name=name, schema=schema, using=MILVUS_ALIAS)
        collection.create_index(
            field_name="vector",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
    else:
        collection = Collection(name=name, using=MILVUS_ALIAS)

    collection.load()
    return collection


class MilvusVectorRepository:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection

    def add(self, payload: MilvusVectorCreate) -> str:
        vector_id = payload.id or uuid4().hex
        self._insert(vector_id, payload.title, payload.payload, payload.vector)
        return vector_id

    def get(self, vector_id: str) -> dict | None:
        rows = self.collection.query(
            expr=f'id == "{_escape_expr(vector_id)}"',
            output_fields=_output_fields(),
            limit=1,
        )
        return rows[0] if rows else None

    def list(self, limit: int) -> list[dict]:
        return self.collection.query(
            expr="created_at_ms >= 0",
            output_fields=_output_fields(),
            limit=limit,
        )

    def update(self, vector_id: str, payload: MilvusVectorUpdate) -> bool:
        current = self.get(vector_id)
        if not current:
            return False

        self.delete(vector_id)
        created_at_ms = int(current["created_at_ms"])
        self._insert(vector_id, payload.title, payload.payload, payload.vector, created_at_ms)
        return True

    def delete(self, vector_id: str) -> bool:
        result = self.collection.delete(expr=f'id == "{_escape_expr(vector_id)}"')
        self.collection.flush()
        return result.delete_count > 0

    def search(self, payload: MilvusSearchRequest) -> list[dict]:
        _validate_vector_dimension(payload.vector)
        results = self.collection.search(
            data=[payload.vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=payload.limit,
            output_fields=["title", "payload_json", "vector", "created_at_ms", "updated_at_ms"],
        )
        rows: list[dict] = []
        for hit in results[0]:
            entity = hit.entity
            rows.append(
                {
                    "id": str(hit.id),
                    "title": entity.get("title"),
                    "payload_json": entity.get("payload_json"),
                    "vector": entity.get("vector"),
                    "created_at_ms": entity.get("created_at_ms"),
                    "updated_at_ms": entity.get("updated_at_ms"),
                    "score": float(hit.score),
                }
            )
        return rows

    def _insert(
        self,
        vector_id: str,
        title: str,
        payload: dict,
        vector: list[float],
        created_at_ms: int | None = None,
    ) -> None:
        _validate_vector_dimension(vector)
        now_ms = _now_ms()
        self.collection.insert(
            [
                [vector_id],
                [title],
                [dumps(payload, ensure_ascii=False)],
                [vector],
                [created_at_ms or now_ms],
                [now_ms],
            ]
        )
        self.collection.flush()


class MilvusVectorService:
    def __init__(self, vectors: MilvusVectorRepository) -> None:
        self.vectors = vectors

    def create_vector(self, payload: MilvusVectorCreate) -> MilvusVectorRead:
        vector_id = self.vectors.add(payload)
        vector = self.vectors.get(vector_id)
        if not vector:
            raise MilvusDemoError("Vector was created but could not be loaded")
        return _to_read(vector)

    def get_vector(self, vector_id: str) -> MilvusVectorRead | None:
        vector = self.vectors.get(vector_id)
        return _to_read(vector) if vector else None

    def list_vectors(self, limit: int) -> list[MilvusVectorRead]:
        return [_to_read(vector) for vector in self.vectors.list(limit)]

    def update_vector(self, vector_id: str, payload: MilvusVectorUpdate) -> bool:
        return self.vectors.update(vector_id, payload)

    def delete_vector(self, vector_id: str) -> bool:
        return self.vectors.delete(vector_id)

    def search_vectors(self, payload: MilvusSearchRequest) -> list[MilvusSearchHit]:
        return [_to_hit(row) for row in self.vectors.search(payload)]


def create_milvus_vector_service() -> MilvusVectorService:
    return MilvusVectorService(MilvusVectorRepository(ensure_milvus_schema()))


def _output_fields() -> list[str]:
    return ["id", "title", "payload_json", "vector", "created_at_ms", "updated_at_ms"]


def _validate_vector_dimension(vector: list[float]) -> None:
    expected = _dimension()
    if len(vector) != expected:
        raise MilvusDemoError(f"Vector dimension must be {expected}, got {len(vector)}")


def _escape_expr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _ms_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _to_read(row: dict) -> MilvusVectorRead:
    return MilvusVectorRead(
        id=str(row["id"]),
        title=str(row["title"]),
        payload=loads(row["payload_json"]),
        vector=[float(item) for item in row["vector"]],
        created_at=_ms_to_datetime(int(row["created_at_ms"])),
        updated_at=_ms_to_datetime(int(row["updated_at_ms"])),
    )


def _to_hit(row: dict) -> MilvusSearchHit:
    vector = _to_read(row)
    return MilvusSearchHit(**vector.model_dump(), score=float(row["score"]))
