from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentConversation(Base):
    """Persisted Multimodal RAG chat thread (history sidebar)."""

    __tablename__ = "agent_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="any", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["AgentConversationMessage"]] = relationship(
        "AgentConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentConversationMessage.id",
    )
    runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="conversation"
    )


class AgentConversationMessage(Base):
    __tablename__ = "agent_conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("agent_conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    agent_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["AgentConversation"] = relationship(
        "AgentConversation", back_populates="messages"
    )
    agent_run: Mapped["AgentRun | None"] = relationship(
        "AgentRun", foreign_keys=[agent_run_id]
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_conversations.id"), nullable=True, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="any", nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    runtime: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped["AgentConversation | None"] = relationship(
        "AgentConversation", back_populates="runs"
    )
    events: Mapped[list["AgentRunEvent"]] = relationship(
        "AgentRunEvent", back_populates="run", cascade="all, delete-orphan"
    )
    citations: Mapped[list["AgentCitation"]] = relationship(
        "AgentCitation", back_populates="run", cascade="all, delete-orphan"
    )


class AgentRunEvent(Base):
    __tablename__ = "agent_run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    message_en: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    message_ko: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="events")


class AgentCitation(Base):
    __tablename__ = "agent_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    cite_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    asset_embedding_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_embeddings.id"), nullable=True
    )
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    snippets_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    t_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    t_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumb_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    segment_note: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="citations")
