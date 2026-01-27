from __future__ import annotations
import datetime

from sqlalchemy import (
    Text,
    ForeignKey,
    DateTime,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func


# 1. Modern SQLAlchemy Base class
class Base(DeclarativeBase):
    pass


# 2. Modern SQLAlchemy model definitions with Mapped and mapped_column
class AlertTemplate(Base):
    """Immutable History: Stores a snapshot of each template version."""

    __tablename__ = "alert_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    # Relationship to TemplateState (optional, but good for ORM queries)
    state: Mapped["TemplateState"] = relationship(back_populates="template_version")

    def __repr__(self):
        return f"<AlertTemplate(id={self.id}, template_key='{self.template_key}', created_at='{self.created_at}')>"


class TemplateState(Base):
    """Mutable State Snapshot: Points to the currently active version of each template."""

    __tablename__ = "template_states"

    template_key: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    active_version_id: Mapped[int] = mapped_column(
        ForeignKey("alert_templates.id"), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationship to AlertTemplate
    template_version: Mapped["AlertTemplate"] = relationship(back_populates="state")

    def __repr__(self):
        return f"<TemplateState(template_key='{self.template_key}', active_version_id={self.active_version_id})>"


def create_db_and_tables(engine):
    Base.metadata.create_all(bind=engine)
