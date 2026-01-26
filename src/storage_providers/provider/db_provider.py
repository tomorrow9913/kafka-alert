from __future__ import annotations

import datetime
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.core.config import settings
from src.schema.alert_schema import TemplateDto
from src.storage_providers.models import AlertTemplate, TemplateState
from src.storage_providers.provider.storage_base import BaseStorageProvider
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class DatabaseProvider(BaseStorageProvider):
    """
    A storage provider that uses a relational database (via SQLAlchemy) as the backend.
    It serves as the primary provider for both reading and writing template data.
    """

    def __init__(self, db_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        db_url = db_url or settings.DATABASE_CONFIG.DATABASE_URL
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self._is_sqlite = self.engine.dialect.name == "sqlite"

    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Provides a transactional scope around a series of operations."""
        db = self.SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            logger.exception("Database transaction failed. Rolling back.")
            raise
        finally:
            db.close()

    def update_check(self, key: str) -> Optional[dict]:
        """
        Checks the `template_states` table for the latest update timestamp for a given key.
        """
        logger.debug(f"Performing update check for key '{key}' in DB.")
        with self.get_db() as db:
            state = (
                db.query(TemplateState)
                .filter(TemplateState.template_key == key)
                .first()
            )

            if not state:
                return None

            return {
                "version_id": state.active_version_id,
                "timestamp": state.updated_at.timestamp(),  # Convert datetime to float
            }

    def _perform_fetch(self, version_id: int, key: str) -> Optional[TemplateDto]:
        """
        Fetches the complete template data by its version ID and constructs the DTO.
        The 'key' parameter is unused here as version_id is a unique primary key.
        """
        logger.debug(f"Performing fetch for version_id '{version_id}' from DB.")
        with self.get_db() as db:
            history = (
                db.query(AlertTemplate).filter(AlertTemplate.id == version_id).first()
            )
            if not history:
                return None

            state = (
                db.query(TemplateState)
                .filter(TemplateState.template_key == history.template_key)
                .first()
            )
            if not state:
                # This case indicates data inconsistency, but we handle it gracefully.
                return None

            return TemplateDto(
                version_id=history.id,
                template_key=history.template_key,
                content=history.content,
                updated_at=state.updated_at,
                updated_by=state.updated_by,
                description=history.description,
            )

    def push(
        self,
        key: str,
        content: str,
        created_by: str,
        desc: Optional[str] = None,
        checkout: bool = True,
    ) -> TemplateDto:
        """
        Creates a new `AlertTemplate` record and optionally checks it out.
        """
        with self.get_db() as db:
            new_history = AlertTemplate(
                template_key=key,
                content=content,
                created_by=created_by,
                description=desc,
            )
            db.add(new_history)
            db.commit()
            db.refresh(new_history)
            logger.info(
                f"Pushed new template version {new_history.id} for key '{key}'."
            )

            if checkout:
                self.checkout(key, new_history.id, created_by)
                # After checkout, a state is guaranteed to exist.
                final_state = (
                    db.query(TemplateState)
                    .filter(TemplateState.template_key == key)
                    .one()
                )
                return TemplateDto(
                    version_id=new_history.id,
                    template_key=new_history.template_key,
                    content=new_history.content,
                    updated_at=final_state.updated_at,
                    updated_by=final_state.updated_by,
                    description=new_history.description,
                )
            else:
                # If not checking out, the state is unchanged. Return a DTO representing
                # the version just created, even if it's not active.
                return TemplateDto(
                    version_id=new_history.id,
                    template_key=new_history.template_key,
                    content=new_history.content,
                    updated_at=new_history.created_at,  # Use history creation time
                    updated_by=new_history.created_by,
                    description=new_history.description,
                )

    def checkout(self, key: str, version_id: int, updated_by: str) -> None:
        """
        Performs an UPSERT on the `template_states` table to set the active version.
        """
        with self.get_db() as db:
            # Ensure the target version exists
            if (
                not db.query(AlertTemplate)
                .filter(AlertTemplate.id == version_id)
                .first()
            ):
                raise ValueError(f"Template version ID '{version_id}' not found.")

            now_utc = datetime.datetime.now(datetime.timezone.utc)

            if self._is_sqlite:
                # Use dialect-specific UPSERT for SQLite
                stmt = sqlite_insert(TemplateState).values(
                    template_key=key,
                    active_version_id=version_id,
                    updated_by=updated_by,
                    updated_at=now_utc,
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
            else:
                # Use session.merge() for other databases (e.g., PostgreSQL)
                state_data = {
                    "template_key": key,
                    "active_version_id": version_id,
                    "updated_by": updated_by,
                    "updated_at": now_utc,
                }
                db.merge(TemplateState(**state_data))

            db.commit()
            logger.info(f"Checked out version {version_id} for key '{key}'.")

            # Invalidate state cache after update
            if key in self._state_cache:
                del self._state_cache[key]

    def delete_version(self, version_id: int, deleted_by: str) -> None:
        """
        Deletes an inactive `AlertTemplate` version.
        """
        with self.get_db() as db:
            # Check if the version is currently active
            is_active = (
                db.query(TemplateState)
                .filter(TemplateState.active_version_id == version_id)
                .first()
            )
            if is_active:
                raise ValueError(
                    f"Cannot delete version {version_id} because it is currently active for key '{is_active.template_key}'."
                )

            # Delete the history record
            history_to_delete = (
                db.query(AlertTemplate).filter(AlertTemplate.id == version_id).first()
            )
            if history_to_delete:
                logger.warning(
                    f"User '{deleted_by}' is deleting template version {version_id} ('{history_to_delete.template_key}')."
                )
                db.delete(history_to_delete)
                db.commit()
                # Content cache for this version_id will now return None, which is correct.
            else:
                raise ValueError(f"Template version ID '{version_id}' not found.")
