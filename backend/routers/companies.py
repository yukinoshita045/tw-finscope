"""
companies.py — /api/companies, /api/industries endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Company, Metric
from backend.schemas import CompanySchema, IndustrySchema

router = APIRouter(prefix="/api", tags=["companies"])

# 產業代碼 → 產業名稱對照表
INDUSTRY_NAMES: dict[str, str] = {
    "01": "水泥工業",
    "02": "食品工業",
    "03": "塑膠工業",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "08": "半導體業",
    "09": "電腦及週邊設備業",
    "10": "光電業",
    "11": "通信網路業",
    "12": "電子零組件業",
    "13": "電子通路業",
    "14": "資訊服務業",
    "15": "其他電子業",
    "20": "建材營造",
    "22": "鋼鐵工業",
    "23": "橡膠工業",
    "24": "汽車工業",
    "25": "其他製造業",
    "26": "航運業",
    "27": "觀光事業",
    "28": "金融保險業",
    "29": "貿易百貨業",
    "30": "油電燃氣業",
    "31": "綜合",
    "32": "生技醫療業",
    "33": "文化創意業",
    "34": "農業科技業",
    "99": "其他",
}


@router.get("/companies", response_model=list[CompanySchema])
def list_companies(
    industry_code: str | None = Query(None, description="產業別代碼"),
    db: Session = Depends(get_db),
):
    """列出公司清單，可按產業過濾"""
    q = db.query(Company)
    if industry_code:
        q = q.filter(Company.industry_code == industry_code)
    companies = q.order_by(Company.company_id).all()

    # 補充 industry_name
    result = []
    for co in companies:
        co_dict = {
            "company_id": co.company_id,
            "short_name": co.short_name,
            "full_name": co.full_name,
            "industry_code": co.industry_code,
            "industry_name": INDUSTRY_NAMES.get(co.industry_code, co.industry_name or ""),
            "en_name": co.en_name,
        }
        result.append(CompanySchema(**co_dict))
    return result


@router.get("/industries", response_model=list[IndustrySchema])
def list_industries(db: Session = Depends(get_db)):
    """列出有資料的產業清單（含公司數）"""
    rows = (
        db.query(Company.industry_code, func.count(Company.company_id).label("cnt"))
        .group_by(Company.industry_code)
        .order_by(Company.industry_code)
        .all()
    )
    result = []
    for row in rows:
        result.append(IndustrySchema(
            industry_code=row.industry_code,
            industry_name=INDUSTRY_NAMES.get(row.industry_code, ""),
            company_count=row.cnt,
        ))
    return result
