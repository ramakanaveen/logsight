from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class QAPair(BaseModel):
    question: str
    answer: str


class ProcessCreate(BaseModel):
    name: str
    description: str
    machine_host: str
    sidecar_port: int = 9000
    log_paths: list[str]
    example_qa: list[QAPair] = []


class ProcessUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    machine_host: str | None = None
    sidecar_port: int | None = None
    log_paths: list[str] | None = None
    example_qa: list[QAPair] | None = None


class ProcessOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    machine_host: str
    sidecar_port: int
    log_paths: list[str]
    example_qa: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


class SourceInfo(BaseModel):
    process: str
    machine: str
    files_searched: int
    lines_matched: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
