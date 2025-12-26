"""Pydantic models for API request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ResearchStatus(str, Enum):
    """Research task status."""

    PENDING = "pending"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    SUMMARIZING = "summarizing"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    ERROR = "error"


class Source(BaseModel):
    """A research source with metadata."""

    url: str
    title: str
    snippet: str
    content: Optional[str] = None
    credibility_score: float = Field(ge=0.0, le=1.0, default=0.5)
    summary: Optional[str] = None


class ResearchRequest(BaseModel):
    """Request to start a research task."""

    topic: str = Field(..., min_length=3, max_length=500)
    depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    include_academic: bool = Field(default=False, description="Include academic sources")


class StreamEvent(BaseModel):
    """Server-sent event for streaming updates."""

    event: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ResearchProgress(BaseModel):
    """Progress update during research."""

    status: ResearchStatus
    message: str
    progress: float = Field(ge=0.0, le=1.0)
    sources_found: int = 0
    sources_processed: int = 0


class ResearchResult(BaseModel):
    """Final research result."""

    topic: str
    briefing: str
    sources: list[Source]
    total_time_seconds: float
    model_used: str


class ChatMessage(BaseModel):
    """A chat message in the conversation."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


# Conversation schemas
class MessageCreate(BaseModel):
    """Create a new message."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class MessageResponse(BaseModel):
    """Message response."""

    id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Create a new conversation."""

    topic: str = Field(..., min_length=3, max_length=500)
    depth: str = Field(default="standard")
    messages: list[MessageCreate] = []


class ConversationUpdate(BaseModel):
    """Update a conversation with research results."""

    briefing: Optional[str] = None
    sources_json: Optional[str] = None
    total_time_seconds: Optional[float] = None
    model_used: Optional[str] = None
    messages: list[MessageCreate] = []


class ConversationResponse(BaseModel):
    """Conversation response."""

    id: int
    topic: str
    depth: str
    briefing: Optional[str] = None
    total_time_seconds: Optional[float] = None
    model_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Conversation list item (without full messages)."""

    id: int
    topic: str
    depth: str
    created_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


# PDF Export schemas
class PDFExportRequest(BaseModel):
    """Request to export a briefing as PDF."""

    topic: str
    briefing: str
    sources: list[Source]
    total_time_seconds: float
    model_used: str
