from __future__ import annotations
import datetime
from typing import List

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    DateTime,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy.sql import func


# 1. Modern SQLAlchemy Base class
class Base(DeclarativeBase):
    pass


# 2. Modern SQLAlchemy model definitions with Mapped and mapped_column
class AlertTemplate(Base):
    """Immutable History: Stores a snapshot of each template version."""

    __tablename__ = "AlertTemplates"

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

    __tablename__ = "TemplateStates"

    template_key: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    active_version_id: Mapped[int] = mapped_column(
        ForeignKey("AlertTemplates.id"), nullable=False
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


class NotificationChannel(Base):
    __tablename__ = "NotificationChannel"
    __table_args__ = (
        PrimaryKeyConstraint("idx", name="NotificationChannel_pkey"),
        Index("responsible_group_idx_event", "responsible_group_idx", "event"),
    )

    idx = mapped_column(BigInteger)
    responsible_group_idx = mapped_column(BigInteger, nullable=False)
    template_key = mapped_column(String(200), nullable=False)
    provider = mapped_column(String(50), nullable=False)
    destination = mapped_column(Text, nullable=False)
    metadata_ = mapped_column("metadata", Text, nullable=False)
    created_at = mapped_column(DateTime(True), nullable=False)
    event = mapped_column(String(100), nullable=False)


class ResponsibleGroup(Base):
    __tablename__ = "ResponsibleGroup"
    __table_args__ = (
        PrimaryKeyConstraint("idx", name="ResponsibleGroup_pkey"),
        UniqueConstraint("name", name="ResponsibleGroup_name_key"),
    )

    idx = mapped_column(BigInteger)
    name = mapped_column(String(50), nullable=False)
    created_at = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()")
    )
    description = mapped_column(Text)

    ResponsibleGroupNode: Mapped[List["ResponsibleGroupNode"]] = relationship(
        "ResponsibleGroupNode", uselist=True, back_populates="ResponsibleGroup_"
    )


class ResponsibleGroupNode(Base):
    __tablename__ = "ResponsibleGroupNode"
    __table_args__ = (
        ForeignKeyConstraint(
            ["responsible_group_idx"],
            ["ResponsibleGroup.idx"],
            name="FK__ResponsibleGroup",
        ),
        PrimaryKeyConstraint("idx", name="ResponsibleGroupNode_pkey"),
        Index("node_name", "node_name"),
    )

    idx = mapped_column(BigInteger)
    responsible_group_idx = mapped_column(BigInteger, nullable=False)
    node_name = mapped_column(String(100), nullable=False)
    created_at = mapped_column(DateTime(True), nullable=False)

    ResponsibleGroup_: Mapped["ResponsibleGroup"] = relationship(
        "ResponsibleGroup", back_populates="ResponsibleGroupNode"
    )


def create_db_and_tables(engine):
    Base.metadata.create_all(bind=engine)
