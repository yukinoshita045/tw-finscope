"""
meta.py — /api/meta endpoint（ETL 最後更新資訊）
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Company, EtlRun, Metric
from backend.schemas import MetaSchema

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=MetaSchema)
def get_meta(db: Session = Depends(get_db)):
    """回傳 ETL 執行狀況與資料量統計"""
    # 最近一次成功 ETL
    latest_run = (
        db.query(EtlRun)
        .filter(EtlRun.status == "success")
        .order_by(EtlRun.finished_at.desc())
        .first()
    )

    total_companies = db.query(func.count(Company.company_id)).scalar() or 0
    total_metrics = db.query(func.count(Metric.id)).scalar() or 0

    return MetaSchema(
        last_etl_run=latest_run.finished_at if latest_run else None,
        etl_status=latest_run.status if latest_run else None,
        total_companies=total_companies,
        total_metric_rows=total_metrics,
    )
