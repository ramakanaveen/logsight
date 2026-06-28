import json
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, TIMESTAMP, ForeignKey, func, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


# ── Topology ──────────────────────────────────────────────────────────────────

class Namespace(Base):
    __tablename__ = "namespaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    machines: Mapped[list["Machine"]] = relationship("Machine", back_populates="namespace", cascade="all, delete-orphan")


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    namespace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("namespaces.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    namespace: Mapped["Namespace"] = relationship("Namespace", back_populates="machines")
    sidecar: Mapped["SidecarInstance | None"] = relationship("SidecarInstance", back_populates="machine", uselist=False, cascade="all, delete-orphan")
    machine_processes: Mapped[list["MachineProcess"]] = relationship("MachineProcess", back_populates="machine", cascade="all, delete-orphan")


class SidecarInstance(Base):
    """One row per running sidecar binary — one per machine."""
    __tablename__ = "sidecar_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, unique=True)
    port: Mapped[int] = mapped_column(Integer, default=9000)
    status: Mapped[str] = mapped_column(String, default="alive")  # alive | dead
    last_heartbeat: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    machine: Mapped["Machine"] = relationship("Machine", back_populates="sidecar")


# ── Process definitions ───────────────────────────────────────────────────────

class ProcessDefinition(Base):
    """Enrichment record for a named process: description + example Q&A."""
    __tablename__ = "process_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    example_qa: Mapped[list] = mapped_column(JsonBlob, default=list)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    machine_processes: Mapped[list["MachineProcess"]] = relationship("MachineProcess", back_populates="process_definition", cascade="all, delete-orphan")


class MachineProcess(Base):
    """Links a Machine to a ProcessDefinition, with the log paths for that process on that machine."""
    __tablename__ = "machine_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    process_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("process_definitions.id", ondelete="CASCADE"), nullable=False)
    log_paths: Mapped[list[str]] = mapped_column(StringArray, nullable=False)

    machine: Mapped["Machine"] = relationship("Machine", back_populates="machine_processes")
    process_definition: Mapped["ProcessDefinition"] = relationship("ProcessDefinition", back_populates="machine_processes")


# ── Conversations ─────────────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JsonBlob, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


# ── Feedback ──────────────────────────────────────────────────────────────────

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = thumbs up, -1 = thumbs down
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
