from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.demo_db.mongo_store import (
    MongoDemoError,
    create_mongo_user_service,
    ensure_mongo_schema,
    get_mongo_client,
)
from app.demo_db.milvus_store import (
    MilvusDemoError,
    connect_milvus,
    create_milvus_vector_service,
    ensure_milvus_schema,
)
from app.demo_db.mysql_store import (
    MySQLDemoError,
    MySQLDemoUserService,
    ensure_mysql_schema,
    get_mysql_engine,
    get_mysql_session_factory,
)
from app.demo_db.schemas import (
    BackendStatus,
    DatabaseLabStatus,
    DemoUserCreate,
    DemoUserEmailUpdate,
    DemoUserRead,
    MilvusSearchHit,
    MilvusSearchRequest,
    MilvusVectorCreate,
    MilvusVectorRead,
    MilvusVectorUpdate,
)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_LAB_HTML = PROJECT_ROOT / "app" / "static" / "database-lab.html"


@router.get("/database-lab", include_in_schema=False)
def database_lab_page() -> FileResponse:
    return FileResponse(DATABASE_LAB_HTML)


@router.get("/api/v1/database-lab/status", response_model=DatabaseLabStatus)
def database_lab_status() -> DatabaseLabStatus:
    return DatabaseLabStatus(
        mysql=_mysql_status(),
        mongodb=_mongodb_status(),
        milvus=_milvus_status(),
    )


@router.post("/api/v1/database-lab/{backend}/users", response_model=DemoUserRead, status_code=201)
def create_user(backend: str, payload: DemoUserCreate) -> DemoUserRead:
    try:
        return _service_for(backend).create_user(payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    except (SQLAlchemyError, PyMongoError, MySQLDemoError, MongoDemoError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/database-lab/{backend}/users", response_model=list[DemoUserRead])
def list_users(
    backend: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DemoUserRead]:
    try:
        return _service_for(backend).list_users(limit=limit)
    except (SQLAlchemyError, PyMongoError, MySQLDemoError, MongoDemoError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/database-lab/{backend}/users/{user_id}", response_model=DemoUserRead)
def get_user(backend: str, user_id: str) -> DemoUserRead:
    try:
        user = _service_for(backend).get_user(user_id)
    except (SQLAlchemyError, PyMongoError, MySQLDemoError, MongoDemoError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/api/v1/database-lab/{backend}/users/{user_id}/email")
def update_user_email(backend: str, user_id: str, payload: DemoUserEmailUpdate) -> dict[str, bool]:
    try:
        updated = _service_for(backend).update_user_email(user_id, str(payload.email))
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    except (SQLAlchemyError, PyMongoError, MySQLDemoError, MongoDemoError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"updated": True}


@router.delete("/api/v1/database-lab/{backend}/users/{user_id}")
def delete_user(backend: str, user_id: str) -> dict[str, bool]:
    try:
        deleted = _service_for(backend).delete_user(user_id)
    except (SQLAlchemyError, PyMongoError, MySQLDemoError, MongoDemoError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@router.post("/api/v1/database-lab/milvus/vectors", response_model=MilvusVectorRead, status_code=201)
def create_vector(payload: MilvusVectorCreate) -> MilvusVectorRead:
    try:
        return create_milvus_vector_service().create_vector(payload)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/database-lab/milvus/vectors", response_model=list[MilvusVectorRead])
def list_vectors(limit: int = Query(default=20, ge=1, le=100)) -> list[MilvusVectorRead]:
    try:
        return create_milvus_vector_service().list_vectors(limit=limit)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/database-lab/milvus/vectors/{vector_id}", response_model=MilvusVectorRead)
def get_vector(vector_id: str) -> MilvusVectorRead:
    try:
        vector = create_milvus_vector_service().get_vector(vector_id)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not vector:
        raise HTTPException(status_code=404, detail="Vector not found")
    return vector


@router.put("/api/v1/database-lab/milvus/vectors/{vector_id}")
def update_vector(vector_id: str, payload: MilvusVectorUpdate) -> dict[str, bool]:
    try:
        updated = create_milvus_vector_service().update_vector(vector_id, payload)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Vector not found")
    return {"updated": True}


@router.delete("/api/v1/database-lab/milvus/vectors/{vector_id}")
def delete_vector(vector_id: str) -> dict[str, bool]:
    try:
        deleted = create_milvus_vector_service().delete_vector(vector_id)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Vector not found")
    return {"deleted": True}


@router.post("/api/v1/database-lab/milvus/search", response_model=list[MilvusSearchHit])
def search_vectors(payload: MilvusSearchRequest) -> list[MilvusSearchHit]:
    try:
        return create_milvus_vector_service().search_vectors(payload)
    except MilvusDemoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _service_for(backend: str):
    if backend == "mysql":
        ensure_mysql_schema()
        SessionLocal = get_mysql_session_factory()
        session = SessionLocal()
        return _ClosingMySQLService(session)
    if backend == "mongodb":
        ensure_mongo_schema()
        return create_mongo_user_service()
    raise HTTPException(status_code=404, detail="Unknown backend")


class _ClosingMySQLService(MySQLDemoUserService):
    def __init__(self, session):
        super().__init__(session)

    def create_user(self, payload: DemoUserCreate) -> DemoUserRead:
        try:
            return super().create_user(payload)
        finally:
            self.session.close()

    def get_user(self, user_id: str) -> DemoUserRead | None:
        try:
            return super().get_user(user_id)
        finally:
            self.session.close()

    def list_users(self, limit: int) -> list[DemoUserRead]:
        try:
            return super().list_users(limit)
        finally:
            self.session.close()

    def update_user_email(self, user_id: str, email: str) -> bool:
        try:
            return super().update_user_email(user_id, email)
        finally:
            self.session.close()

    def delete_user(self, user_id: str) -> bool:
        try:
            return super().delete_user(user_id)
        finally:
            self.session.close()


def _mysql_status() -> BackendStatus:
    try:
        ensure_mysql_schema()
        with get_mysql_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return BackendStatus(backend="mysql", ok=True, message="MySQL connected")
    except Exception as exc:
        return BackendStatus(backend="mysql", ok=False, message=str(exc))


def _mongodb_status() -> BackendStatus:
    try:
        get_mongo_client().admin.command("ping")
        ensure_mongo_schema()
        return BackendStatus(backend="mongodb", ok=True, message="MongoDB connected")
    except Exception as exc:
        return BackendStatus(backend="mongodb", ok=False, message=str(exc))


def _milvus_status() -> BackendStatus:
    try:
        connect_milvus()
        ensure_milvus_schema()
        return BackendStatus(backend="milvus", ok=True, message="Milvus connected")
    except Exception as exc:
        return BackendStatus(backend="milvus", ok=False, message=str(exc))
