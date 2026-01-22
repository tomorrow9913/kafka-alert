# -*- coding: utf-8 -*-
# src/utils/alert/schema.py
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, model_validator


class Provider(str, Enum):
    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"


class AlertPayload(BaseModel):
    provider: Provider
    template: Optional[str] = None
    template_content: Optional[str] = None
    data: Dict[str, Any]
    destination: Optional[str] = None

    @model_validator(mode="after")
    def check_template_xor_template_content(self):
        if self.template is None and self.template_content is None:
            raise ValueError("Either 'template' or 'template_content' must be set.")
        if self.template is not None and self.template_content is not None:
            raise ValueError(
                "Both 'template' and 'template_content' cannot be set at the same time."
            )
        return self
