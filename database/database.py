from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

username = os.getenv("POSTGRES_USER", "temp_admin")
password = os.getenv("POSTGRES_PASSWORD", "temp_password")
host = os.getenv("POSTGRES_HOST", "localhost")
database = os.getenv("POSTGRES_DB", "yamong_postgres")
port = os.getenv("POSTGRES_PORT", "5432")

if not username or not password or not host or not database:
    raise ValueError("Please set the environment variables for the database")

DB_URL = f"postgresql://{username}:{password}@{host}:{port}/{database}"

engine = {
    'project': create_engine(
        DB_URL,
        pool_pre_ping=True,  # 연결 체크
        pool_recycle=300,    # 연결 재활용
        connect_args={
            "connect_timeout": 10
        })
}

project_base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False)
SessionLocal.configure(binds={
    project_base: engine['project']
})

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()