import json
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, TIMESTAMP, func, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class StringArray(TypeDecorator):
    """Stores list[str] as PostgreSQL ARRAY on Postgres, JSON text on other backends."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String()))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        return json.loads(value) if value is not None else None


class JsonBlob(TypeDecorator):
    """Stores list/dict as PostgreSQL JSONB on Postgres, JSON text on other backends."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        return json.loads(value) if value is not None else None


class Base(DeclarativeBase):
    pass


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    machine_host: Mapped[str] = mapped_column(String, nullable=False)
    sidecar_port: Mapped[int] = mapped_column(Integer, default=9000)
    log_paths: Mapped[list[str]] = mapped_column(StringArray, nullable=False)
    example_qa: Mapped[list] = mapped_column(JsonBlob, default=list)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
