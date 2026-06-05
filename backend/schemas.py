"""
schemas.py — Pydantic 回應模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CompanySchema(BaseModel):
    company_id: str
    short_name: str
    full_name: str
    industry_code: str
    industry_name: str
    en_name: str

    model_config = {"from_attributes": True}


class IndustrySchema(BaseModel):
    industry_code: str
    industry_name: str
    company_count: int


class MetricSchema(BaseModel):
    company_id: str
    year: int
    season: int
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_ratio: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_income_yoy: Optional[float] = None
    operating_income_yoy: Optional[float] = None

    model_config = {"from_attributes": True}


class TimeseriesPoint(BaseModel):
    year: int
    season: int
    period_label: str  # 例："2024 Q3"
    value: Optional[float]


class RankingItem(BaseModel):
    company_id: str
    short_name: str
    industry_code: str
    year: int
    season: int
    metric_value: Optional[float]
    rank: int


class MetaSchema(BaseModel):
    last_etl_run: Optional[datetime]
    etl_status: Optional[str]
    total_companies: int
    total_metric_rows: int
