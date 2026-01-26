from __future__ import annotations
import datetime

from sqlalchemy import (
    create_engine,
    Text,
    ForeignKey,
    DateTime,
    String,
)
from sqlalchemy.orm import (
    sessionmaker,
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


if __name__ == "__main__":
    from src.core.config import settings
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    DATABASE_URL = settings.DATABASE_CONFIG.DATABASE_URL
    engine = create_engine(DATABASE_URL)

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating database and tables...")
    create_db_and_tables(engine)
    print("Database and tables created.")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. Create History (Push)
        v1 = AlertTemplate(
            template_key="test/email",
            content="Hello {{ name }}, this is version 1.",
            created_by="system_init",
            description="Initial version",
        )
        v2 = AlertTemplate(
            template_key="test/email",
            content="Hello {{ name }}, this is the updated version 2!",
            created_by="user_a",
            description="Second version with updates",
        )
        db.add_all([v1, v2])
        db.commit()
        db.refresh(v1)
        db.refresh(v2)
        print(f"Created history versions: ID {v1.id} and ID {v2.id}")

        # 2. Create State (Checkout) - UPSERT
        stmt = sqlite_insert(TemplateState).values(
            template_key="test/email",
            active_version_id=v2.id,
            updated_by="user_a",
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )
        on_update_stmt = stmt.on_conflict_do_update(
            index_elements=["template_key"],
            set_={
                "active_version_id": stmt.excluded.active_version_id,
                "updated_by": stmt.excluded.updated_by,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        db.execute(on_update_stmt)
        db.commit()

        print("Test data inserted successfully. 'test/email' is now at version 2.")

        # 3. Verify data
        final_state = db.query(TemplateState).filter_by(template_key="test/email").one()
        print(f"Verified state: {final_state}")
        assert final_state.active_version_id == v2.id

    except Exception as e:
        print(f"Error inserting test data: {e}")
        db.rollback()
    finally:
        db.close()
