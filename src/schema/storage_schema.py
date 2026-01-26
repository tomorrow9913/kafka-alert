from __future__ import annotations
from dataclasses import dataclass
import datetime
from typing import Optional


@dataclass
class TemplateHistory:
    """템플릿 이력 저장소 DTO"""

    id: int
    key: str
    content: str
    created_at: datetime.datetime
    created_by: str
    description: Optional[str] = None


@dataclass
class StateLog:
    """상태 로그 저장소 DTO"""

    key: str
    version_id: int
    version_timestamp: datetime.datetime
    created_at: datetime.datetime
    created_by: str
    reason: Optional[str] = None
