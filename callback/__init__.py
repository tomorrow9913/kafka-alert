import os
from pathlib import Path
from typing import NamedTuple

class Callback(NamedTuple):
   name: str
   func: callable

callbacks = {}
base_path = Path(os.path.dirname(__file__))

# 하위 디렉토리 순회
for dir_path in [d for d in base_path.iterdir() if d.is_dir() and d.name != '__pycache__']:
   callbacks[dir_path.name] = []
   
   # 각 디렉토리 내 .py 파일 처리
   for file_path in [f for f in dir_path.iterdir() if f.suffix == '.py' and f.name != '__init__.py']:
      module = __import__(f'callback.{dir_path.name}.{file_path.stem}', fromlist=['callback'])
      
      callbacks[dir_path.name].append(Callback(
         name=file_path.stem,
         func=module.callback
      ))