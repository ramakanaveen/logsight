from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class QAPair(BaseModel):
    question: str
    answer: str


# ── Process Definitions ───────────────────────────────────────────────────────

class ProcessDefinitionCreate(BaseModel):
    name: str
    description: str = ""
    example_qa: list[QAPair] = []


class ProcessDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    example_qa: list[QAPair] | None = None


class ProcessDefinitionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    example_qa: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Topology ──────────────────────────────────────────────────────────────────

class NamespaceCreate(BaseModel):
    name: str
    description: str = ""


class NamespaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class NamespaceOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MachineCreate(BaseModel):
    hostname: str
    description: str = ""


class MachineUpdate(BaseModel):
    hostname: str | None = None
    description: str | None = None


class MachineOut(BaseModel):
    id: uuid.UUID
    namespace_id: uuid.UUID
    hostname: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SidecarInstanceOut(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    port: int
    status: str
    last_heartbeat: datetime
    registered_at: datetime

    model_config = {"from_attributes": True}


class SidecarRegisterRequest(BaseModel):
    machine_host: str
    port: int = 9000


class SidecarRegisterResponse(BaseModel):
    sidecar_id: uuid.UUID


class MachineProcessCreate(BaseModel):
    process_definition_id: uuid.UUID
    log_paths: list[str]


class MachineProcessOut(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    process_definition_id: uuid.UUID
    process_name: str
    log_paths: list[str]

    model_config = {"from_attributes": True}


class ProcessInTopology(BaseModel):
    id: uuid.UUID
    name: str
    log_paths: list[str]


class MachineInTopology(BaseModel):
    machine: MachineOut
    sidecar: SidecarInstanceOut | None
    processes: list[ProcessInTopology]


class NamespaceTopology(BaseModel):
    namespace: NamespaceOut
    machines: list[MachineInTopology]


# ── Chat / Conversations ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: uuid.UUID | None = None
    process_hint: str | None = None  # name of a process hinted via /slash-command


class SourceInfo(BaseModel):
    process: str
    machine: str
    files_searched: int
    lines_matched: int
    matched_files: list[str] = []


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class FeedbackCreate(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    rating: int  # 1 = thumbs up, -1 = thumbs down
    comment: str = ""


class FeedbackOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    conversation_id: uuid.UUID


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── SSE event envelope ────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    type: str
    data: Any
