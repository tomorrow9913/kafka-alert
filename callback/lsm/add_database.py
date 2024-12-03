from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database.database import get_db
from database import models

async def callback(key: str, value: dict) -> bool:
    db = next(get_db())
    try: 
        create_lsm_log(db, value)
    except Exception as e:
        raise
    return True

def create_lsm_log(db: Session, data: dict):
    try:
        # timestamp 문자열을 float로 변환 후 datetime 객체로 생성
        timestamp_float = float(data['timestamp'].split()[1])
        timestamp = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
    except ValueError:
        # 파싱 실패 시 현재 시간 사용
        timestamp = datetime.now(timezone.utc)
        
    db_log = models.LsmLog(
        path=data['data']['path'],
        source=data['data']['source'],
        comm=data['command'],
        pid=data['process']['pid'],
        ppid=data['process']['ppid'],
        host_pid=data['process']['host_pid'],
        host_ppid=data['process']['host_ppid'],
        uid=data['process']['uid'],
        event_id=data['event_id'],
        cgroup_id=data['cgroup_id'],
        mnt_ns=data['container_id']['mnt_ns'],
        pid_ns=data['container_id']['pid_ns'],
        ret_val=data['return_value'],
        timestamp=timestamp
    )

    try:
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    except Exception as e:
        db.rollback()
        raise e
