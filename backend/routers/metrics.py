"""
metrics.py — /api/metrics, /api/timeseries, /api/ranking endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Company, Metric
from backend.schemas import MetricSchema, RankingItem, TimeseriesPoint

router = APIRouter(prefix="/api", tags=["metrics"])

VALID_METRICS = {
    "revenue", "gross_profit", "operating_income", "net_income",
    "gross_margin", "operating_margin", "net_margin",
    "roe", "roa", "current_ratio", "debt_ratio",
    "revenue_yoy", "net_income_yoy", "eps_basic", "free_cash_flow",
}


@router.get("/metrics", response_model=list[MetricSchema])
def get_metrics(
    company_id: str | None = Query(None),
    company_ids: str | None = Query(None, description="逗號分隔的公司代號"),
    from_year: int | None = Query(None, alias="from"),
    to_year: int | None = Query(None, alias="to"),
    season: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    取得財務指標資料
    - company_id: 單一公司
    - company_ids: 多家公司（逗號分隔）
    - from/to: 年度範圍
    """
    q = db.query(Metric)
    ids = []
    if company_id:
        ids.append(company_id)
    if company_ids:
        ids.extend([x.strip() for x in company_ids.split(",") if x.strip()])
    if ids:
        q = q.filter(Metric.company_id.in_(ids))
    if from_year:
        q = q.filter(Metric.year >= from_year)
    if to_year:
        q = q.filter(Metric.year <= to_year)
    if season:
        q = q.filter(Metric.season == season)

    return q.order_by(Metric.company_id, Metric.year, Metric.season).all()


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def get_timeseries(
    company_id: str = Query(..., description="公司代號"),
    metric: str = Query(..., description="指標名稱"),
    from_year: int = Query(2022, alias="from"),
    to_year: int = Query(2025, alias="to"),
    db: Session = Depends(get_db),
):
    """
    取得單一公司某指標的時間序列
    """
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"Invalid metric. Valid options: {sorted(VALID_METRICS)}")

    rows = (
        db.query(Metric)
        .filter(
            Metric.company_id == company_id,
            Metric.year >= from_year,
            Metric.year <= to_year,
        )
        .order_by(Metric.year, Metric.season)
        .all()
    )

    result = []
    for row in rows:
        result.append(TimeseriesPoint(
            year=row.year,
            season=row.season,
            period_label=f"{row.year} Q{row.season}",
            value=getattr(row, metric, None),
        ))
    return result


@router.get("/ranking", response_model=list[RankingItem])
def get_ranking(
    metric: str = Query(..., description="排名指標"),
    year: int = Query(...),
    season: int = Query(...),
    industry_code: str | None = Query(None),
    limit: int = Query(20),
    db: Session = Depends(get_db),
):
    """
    產業排名：特定季度，按某指標排名前 N 家
    """
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"Invalid metric.")

    metric_col = getattr(Metric, metric)

    q = (
        db.query(
            Metric.company_id,
            Company.short_name,
            Company.industry_code,
            Metric.year,
            Metric.season,
            metric_col.label("metric_value"),
        )
        .join(Company, Metric.company_id == Company.company_id)
        .filter(
            Metric.year == year,
            Metric.season == season,
            metric_col.isnot(None),
        )
    )
    if industry_code:
        q = q.filter(Company.industry_code == industry_code)

    rows = q.order_by(metric_col.desc()).limit(limit).all()

    result = []
    for i, row in enumerate(rows, 1):
        result.append(RankingItem(
            company_id=row.company_id,
            short_name=row.short_name or "",
            industry_code=row.industry_code or "",
            year=row.year,
            season=row.season,
            metric_value=row.metric_value,
            rank=i,
        ))
    return result


@router.get("/industry-average", response_model=list[TimeseriesPoint])
def get_industry_average(
    industry_code: str = Query(..., description="產業別代碼"),
    metric: str = Query(..., description="指標名稱"),
    from_year: int = Query(2022, alias="from"),
    to_year: int = Query(2025, alias="to"),
    db: Session = Depends(get_db),
):
    """
    產業平均時間序列(創意加分:讓使用者把單一公司和同產業平均對比)
    回傳該產業所有公司在每個 (year, season) 的平均值。
    """
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"Invalid metric. Valid: {sorted(VALID_METRICS)}")

    metric_col = getattr(Metric, metric)

    rows = (
        db.query(
            Metric.year,
            Metric.season,
            func.avg(metric_col).label("avg_value"),
            func.count(metric_col).label("n"),
        )
        .join(Company, Metric.company_id == Company.company_id)
        .filter(
            Company.industry_code == industry_code,
            Metric.year >= from_year,
            Metric.year <= to_year,
            metric_col.isnot(None),
        )
        .group_by(Metric.year, Metric.season)
        .order_by(Metric.year, Metric.season)
        .all()
    )

    result = []
    for row in rows:
        result.append(TimeseriesPoint(
            year=row.year,
            season=row.season,
            period_label=f"{row.year} Q{row.season}",
            value=float(row.avg_value) if row.avg_value is not None else None,
        ))
    return result
