# -*- coding: utf-8 -*-
import logging
import sys
from logging import LogRecord
from pathlib import Path
from types import FrameType
from typing import Optional, Set

import apprise
from loguru import logger

from core.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercepts standard `logging` logs and redirects them to `loguru`.
    """

    def emit(self, record: LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Optional[FrameType] = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger_with_name = logger.bind(name=record.name)
        logger_with_name.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class _LogManager:
    """
    Singleton class for managing the application's logging system.
    """

    def __init__(self):
        self._configured_loggers: Set[str] = set()
        self.log_dir = Path(settings.APP_CONFIG.LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.remove()
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

        logger.patch(lambda record: record["extra"].setdefault("name", "unnamed"))

        # Default console logger
        logger.add(
            sys.stdout,
            level=settings.APP_CONFIG.LOG_LEVEL.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[name]:<15}</cyan> | "
                "<cyan>{name}</cyan>:<cyan>{function}:{line}</cyan> - <level>{message}</level>"
            ),
            colorize=True,
        )

        # Apprise notification logger for ERROR level
        if settings.APP_CONFIG.LOG_NOTIFIER_URL:
            notifier = apprise.Apprise()
            notifier.add(settings.APP_CONFIG.LOG_NOTIFIER_URL)
            logger.add(
                lambda msg: notifier.notify(body=msg),
                level="ERROR",
                filter=lambda record: not record["extra"].get("no_notify", False),
                format="[{extra[name]}] {message}",
            )

    def get_logger(self, name: str, no_notify: bool = False):
        """
        Gets or creates a logger with the specified name.
        """
        if name not in self._configured_loggers:
            log_file_path = self.log_dir / f"{name}.log"
            logger.add(
                log_file_path,
                level=settings.APP_CONFIG.LOG_LEVEL.upper(),
                filter=lambda record: record["extra"].get("name") == name,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=f"{settings.APP_CONFIG.LOG_MAX_BYTES} B",
                retention=f"{settings.APP_CONFIG.LOG_BACKUP_COUNT} days",
                compression="zip",
                encoding="utf-8",
                enqueue=True,
                backtrace=settings.APP_CONFIG.ENV != "prod",
                diagnose=settings.APP_CONFIG.ENV != "prod",
            )
            self._configured_loggers.add(name)

        return logger.bind(name=name, no_notify=no_notify)


# Singleton instance
LogManager = _LogManager()
