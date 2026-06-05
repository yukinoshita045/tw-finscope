"""
db.py — SQLAlchemy engine 與 session 設定

支援 PostgreSQL(生產) 與 SQLite(本地開發/示範) 兩種資料庫。
透過 DATABASE_URL 環境變數切換:
  postgresql://user:pass@host:5432/db  (生產)
  sqlite:///./tw_finscope.db           (本地)
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tw_finscope.db",  # 預設使用 SQLite,免設 Postgres 也能跑
)

# Render / Heroku 有時給 postgres:// 舊式 URI,sqlalchemy 需要 postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite 與 Postgres 引擎參數不同
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # FastAPI 多 thread 需要
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency:產生一個 DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
