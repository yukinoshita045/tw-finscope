"""
models.py — SQLAlchemy ORM 模型（對應 DB schema）
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(String(10), primary_key=True)
    short_name = Column(String(50))
    full_name = Column(String(100))
    industry_code = Column(String(10), index=True)
    industry_name = Column(String(50))
    en_name = Column(String(100))


class Statement(Base):
    """原始財報 line items（正規化長表）"""
    __tablename__ = "statements"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "year", "season", "statement_type", "line_item_key",
            name="uq_statement_item"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String(10), index=True, nullable=False)
    year = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    statement_type = Column(String(20), nullable=False)  # balance / income / cash_flow
    line_item_key = Column(String(100), nullable=False)
    value = Column(Float)


class Metric(Base):
    """衍生財務指標（gold table）"""
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("company_id", "year", "season", name="uq_metric_period"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String(10), index=True, nullable=False)
    year = Column(Integer, nullable=False, index=True)
    season = Column(Integer, nullable=False)

    # 損益
    revenue = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    eps_basic = Column(Float)
    eps_diluted = Column(Float)

    # 資產負債
    total_assets = Column(Float)
    total_equity = Column(Float)
    total_liabilities = Column(Float)
    current_assets = Column(Float)
    current_liabilities = Column(Float)
    operating_cash_flow = Column(Float)
    free_cash_flow = Column(Float)

    # 利潤率 (%)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)

    # 報酬率 (%)
    roe = Column(Float)
    roa = Column(Float)

    # 比率
    current_ratio = Column(Float)
    debt_ratio = Column(Float)

    # YoY 成長率 (%)
    revenue_yoy = Column(Float)
    net_income_yoy = Column(Float)
    operating_income_yoy = Column(Float)


class EtlRun(Base):
    """ETL 執行記錄（powers Last Updated badge）"""
    __tablename__ = "etl_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    companies_processed = Column(Integer, default=0)
    rows_upserted = Column(Integer, default=0)
    status = Column(String(20), default="running")  # running / success / error
    notes = Column(String(500))
