from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class DemoUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    age: int = Field(ge=1, le=130)

    model_config = ConfigDict(extra="forbid")


class DemoUserEmailUpdate(BaseModel):
    email: EmailStr

    model_config = ConfigDict(extra="forbid")


class DemoUserRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    age: int
    created_at: datetime
    updated_at: datetime


class BackendStatus(BaseModel):
    backend: str
    ok: bool
    message: str


class DatabaseLabStatus(BaseModel):
    mysql: BackendStatus
    mongodb: BackendStatus
    milvus: BackendStatus


class MilvusVectorCreate(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    vector: list[float] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("vector")
    @classmethod
    def vector_must_be_numbers(cls, value: list[float]) -> list[float]:
        return [float(item) for item in value]


class MilvusVectorUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    vector: list[float] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("vector")
    @classmethod
    def vector_must_be_numbers(cls, value: list[float]) -> list[float]:
        return [float(item) for item in value]


class MilvusSearchRequest(BaseModel):
    vector: list[float] = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)

    model_config = ConfigDict(extra="forbid")

    @field_validator("vector")
    @classmethod
    def vector_must_be_numbers(cls, value: list[float]) -> list[float]:
        return [float(item) for item in value]


class MilvusVectorRead(BaseModel):
    id: str
    title: str
    payload: dict[str, Any]
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class MilvusSearchHit(MilvusVectorRead):
    score: float
