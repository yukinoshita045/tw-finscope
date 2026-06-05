"""
seed_demo.py — 在沒有網路或 MOPS 被擋時,灌入合成但合理的示範資料

用法:
    # 預設寫入 SQLite (tw_finscope.db),立即可被 FastAPI 讀取
    python -m pipeline.seed_demo

    # 指定其他 DB
    DATABASE_URL=postgresql://... python -m pipeline.seed_demo

特色:
    - 8 家代表性公司 × 16 季 (2022 Q1 ~ 2025 Q4)
    - 用真實財務比率區間生成合理數字(不是隨機 noise)
    - 每家公司有自己的「公司性格」(高毛利/低毛利、穩健/波動 等)
    - 自動寫一筆 etl_run 讓 LastUpdatedBadge 有東西可顯示

這是 demo 時的安全網。實際資料以 run_etl.py 從 MOPS 拉取為準。
"""

from __future__ import annotations

import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import SessionLocal, engine
from backend.models import Base
from pipeline.load import (
    create_etl_run,
    finish_etl_run,
    upsert_company,
    upsert_metrics,
    upsert_statements,
)
from pipeline.transform import compute_metrics, compute_yoy

random.seed(42)

# (company_id, short_name, full_name, industry_code, en_name, archetype)
# archetype 決定基本數字級數與比率特性
# 對應 backend/routers/companies.py 內 INDUSTRY_NAMES 的真實 TWSE 產業代碼
DEMO_COMPANIES = [
    ("2330", "台積電",   "台灣積體電路製造股份有限公司", "08", "TSMC",     "high_margin_tech"),
    ("2454", "聯發科",   "聯發科技股份有限公司",         "08", "MediaTek", "high_margin_tech"),
    ("2317", "鴻海",     "鴻海精密工業股份有限公司",     "09", "Hon Hai",  "low_margin_em"),
    ("2382", "廣達",     "廣達電腦股份有限公司",         "09", "Quanta",   "low_margin_em"),
    ("2882", "國泰金",   "國泰金融控股股份有限公司",     "28", "Cathay",   "financial"),
    ("2881", "富邦金",   "富邦金融控股股份有限公司",     "28", "Fubon",    "financial"),
    ("1216", "統一",     "統一企業股份有限公司",         "02", "Uni-Pres", "consumer_staple"),
    ("1301", "台塑",     "台灣塑膠工業股份有限公司",     "03", "FPC",      "cyclical"),
]

INDUSTRY_NAME = {
    "08": "半導體業",
    "09": "電腦及週邊設備業",
    "28": "金融保險業",
    "02": "食品工業",
    "03": "塑膠工業",
}

# 不同 archetype 的基本財務參數
# scale = 營收量級(新台幣元), 其他為比率(0~1)
ARCHETYPE = {
    "high_margin_tech": dict(
        scale=4e11, gross=0.52, op=0.42, net=0.38, roa=0.18, roe=0.28,
        cr=2.4, dr=0.32, yoy_mu=0.12, yoy_sigma=0.10, volatility=0.06,
    ),
    "low_margin_em": dict(
        scale=1.5e12, gross=0.08, op=0.03, net=0.025, roa=0.04, roe=0.10,
        cr=1.3, dr=0.55, yoy_mu=0.05, yoy_sigma=0.12, volatility=0.08,
    ),
    "financial": dict(
        scale=6e10, gross=0.42, op=0.30, net=0.22, roa=0.012, roe=0.11,
        cr=1.1, dr=0.92, yoy_mu=0.06, yoy_sigma=0.15, volatility=0.10,
    ),
    "consumer_staple": dict(
        scale=1.2e11, gross=0.32, op=0.08, net=0.06, roa=0.06, roe=0.13,
        cr=1.4, dr=0.50, yoy_mu=0.04, yoy_sigma=0.06, volatility=0.04,
    ),
    "cyclical": dict(
        scale=2e11, gross=0.18, op=0.10, net=0.07, roa=0.05, roe=0.11,
        cr=1.7, dr=0.45, yoy_mu=0.02, yoy_sigma=0.18, volatility=0.12,
    ),
}


def _wiggle(base: float, vol: float) -> float:
    return base * (1 + random.gauss(0, vol))


def _quarter_seasonality(season: int) -> float:
    """讓 Q4 比 Q1 高一些,符合許多公司營收分布"""
    return {1: 0.92, 2: 0.98, 3: 1.02, 4: 1.08}[season]


def generate_period(arch_key: str, year: int, season: int, year_idx: int) -> tuple[dict, dict, dict]:
    """
    產生一個期間的(balance, income, cash_flow)三份報表 line items dict。
    year_idx = 從第一年開始的相對年(0,1,2,3),用來模擬成長趨勢。
    """
    arch = ARCHETYPE[arch_key]
    vol = arch["volatility"]

    # 整體規模隨年份慢慢增長
    growth = (1 + arch["yoy_mu"]) ** year_idx
    seasonal = _quarter_seasonality(season)
    revenue = arch["scale"] * growth * seasonal * (1 + random.gauss(0, vol))
    gross_profit = revenue * _wiggle(arch["gross"], vol * 0.5)
    op_income = revenue * _wiggle(arch["op"], vol * 0.6)
    net_income = revenue * _wiggle(arch["net"], vol * 0.7)

    total_assets = revenue / max(arch["roa"], 0.01) * _wiggle(1.0, vol * 0.3) * 0.25
    # ROA = net/assets;用本季 net 反推 assets 量級;0.25 是季→年化粗略
    total_equity = total_assets * (1 - _wiggle(arch["dr"], vol * 0.3))
    total_liab = total_assets - total_equity
    curr_assets = total_assets * _wiggle(0.45, vol * 0.4)
    curr_liab = curr_assets / max(arch["cr"], 0.5) * _wiggle(1.0, vol * 0.3)
    op_cf = net_income * _wiggle(1.15, vol * 0.5)
    capex = revenue * _wiggle(0.10, vol * 0.6)

    income = {
        "revenue": revenue,
        "gross_profit": gross_profit,
        "operating_income": op_income,
        "net_income": net_income,
        "eps_basic": net_income / 1e10 * _wiggle(1.0, vol * 0.4),
        "eps_diluted": net_income / 1e10 * _wiggle(0.98, vol * 0.4),
    }
    balance = {
        "total_assets": total_assets,
        "total_equity": total_equity,
        "total_liabilities": total_liab,
        "total_current_assets": curr_assets,
        "total_current_liabilities": curr_liab,
    }
    cash_flow = {
        "operating_cash_flow": op_cf,
        "capex": capex,
    }
    return balance, income, cash_flow


def seed(years=range(2022, 2026)) -> None:
    print("[seed] 建立 DB 表…")
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    run_id = None
    rows_upserted = 0

    try:
        run_id = create_etl_run(session, notes="demo seed (synthetic)")
        session.commit()

        # 1. 公司基本資料
        for cid, sname, fname, ind, en, _arch in DEMO_COMPANIES:
            upsert_company(session, {
                "company_id": cid,
                "short_name": sname,
                "full_name": fname,
                "industry_code": ind,
                "industry_name": INDUSTRY_NAME.get(ind, ""),
                "en_name": en,
            })
        session.commit()

        # 2. 對每家公司、每季產生並 upsert
        for cid, sname, _full, _ind, _en, arch_key in DEMO_COMPANIES:
            print(f"[seed] {cid} {sname} ({arch_key})")
            metrics_cache: dict[tuple[int, int], dict] = {}
            for year_idx, year in enumerate(years):
                for season in (1, 2, 3, 4):
                    bs, inc, cf = generate_period(arch_key, year, season, year_idx)
                    metrics = compute_metrics(bs, inc, cf)
                    prev = metrics_cache.get((year - 1, season))
                    if prev:
                        metrics.update(compute_yoy(metrics, prev))
                    metrics_cache[(year, season)] = metrics

                    upsert_statements(session, cid, year, season, "balance", bs)
                    upsert_statements(session, cid, year, season, "income", inc)
                    upsert_statements(session, cid, year, season, "cash_flow", cf)
                    upsert_metrics(session, cid, year, season, metrics)
                    rows_upserted += len(bs) + len(inc) + len(cf)
            session.commit()

        finish_etl_run(
            session, run_id,
            companies_processed=len(DEMO_COMPANIES),
            rows_upserted=rows_upserted,
            status="success",
            notes="demo seed completed",
        )
        print(f"\n[seed] 完成。公司 {len(DEMO_COMPANIES)} 家、約 {rows_upserted} 筆 line items。")
    except Exception as e:
        print(f"[seed] 錯誤:{e}")
        if run_id is not None:
            finish_etl_run(
                session, run_id,
                companies_processed=0,
                rows_upserted=rows_upserted,
                status="error",
                notes=str(e)[:400],
            )
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
