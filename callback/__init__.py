# -*- coding: utf-8 -*-
import os
import importlib
from pathlib import Path
from typing import NamedTuple, Callable, Dict, List

from utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class Callback(NamedTuple):
    name: str
    func: Callable
    z_index: int = 0


callbacks: Dict[str, List[Callback]] = {}
base_path = Path(os.path.dirname(__file__))

logger.info(f"Loading callbacks from {base_path}")

# 하위 디렉토리 순회
for dir_path in [
    d for d in base_path.iterdir() if d.is_dir() and d.name != "__pycache__"
]:
    callbacks[dir_path.name] = []

    logger.info(f"Loading callbacks from {dir_path}")
    # 각 디렉토리 내 .py 파일 처리
    for file_path in [
        f for f in dir_path.iterdir() if f.suffix == ".py" and f.name != "__init__.py"
    ]:
        module_name = f"callback.{dir_path.name}.{file_path.stem}"
        module = importlib.import_module(module_name)

        alert_disable = getattr(module, "ALERT_DISABLE", False)
        z_index = getattr(module, "Z_INDEX", 0)
        logger.info(
            f"File: {dir_path.name}.{file_path.stem}: DISABLE: {alert_disable} Z_INDEX: {z_index}"
        )
        if alert_disable:
            continue

        callbacks[dir_path.name].append(
            Callback(name=file_path.stem, func=module.callback, z_index=z_index)
        )

    # z-index로 정렬
    callbacks[dir_path.name].sort(key=lambda x: x.z_index)
