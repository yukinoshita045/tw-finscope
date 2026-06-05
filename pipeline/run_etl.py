"""
run_etl.py — ETL 主程式

執行方式：
  python -m pipeline.run_etl
  python -m pipeline.run_etl --companies 2330 2317 2454
  python -m pipeline.run_etl --industry 08  (半導體)
  python -m pipeline.run_etl --all          (全部公司)

環境變數：
  DATABASE_URL  — PostgreSQL 連線字串
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

# 加入專案根目錄到 sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.db import SessionLocal, engine
from backend.models import Base
from pipeline.extract import available_periods, fetch_all_statements
from pipeline.load import (
    create_etl_run,
    finish_etl_run,
    upsert_company,
    upsert_metrics,
    upsert_statements,
)
from pipeline.transform import compute_metrics, compute_yoy, parse_statement_rows

COMPANIES_JSON = Path(__file__).parent / "companies.json"

# 優先跑的公司（各產業代表性企業，共 40 家）
PRIORITY_COMPANIES = [
    # 半導體 (08)
    "2330",  # 台積電
    "2303",  # 聯電
    "2379",  # 瑞昱
    "2454",  # 聯發科
    "3711",  # 日月光投控
    # 電子零組件 (23)
    "2317",  # 鴻海
    "2354",  # 鴻準
    "2382",  # 廣達
    "2357",  # 華碩
    "2353",  # 宏碁
    # 金融 (28 財務保險)
    "2882",  # 國泰金
    "2881",  # 富邦金
    "2886",  # 兆豐金
    "2884",  # 玉山金
    "2883",  # 開發金
    # 食品 (02)
    "1216",  # 統一
    "1210",  # 大成
    "1225",  # 福懋油
    "1201",  # 味全
    "2911",  # 麗嬰房
    # 傳統產業 - 水泥玻璃 (01)
    "1101",  # 台泥
    "1102",  # 亞泥
    "1103",  # 嘉泥
    # 鋼鐵 (22)
    "2002",  # 中鋼
    "2006",  # 東和鋼鐵
    # 汽車 (24)
    "2201",  # 裕隆
    "2204",  # 中華汽車
    # 電信 (30)
    "2412",  # 中華電
    "3045",  # 台灣大哥大
    "4904",  # 遠傳
    # 百貨零售 (25)
    "2912",  # 統一超
    "2915",  # 潤泰全
    # 石化 (10)
    "1301",  # 台塑
    "1303",  # 南亞
    "1326",  # 台化
    # 電機機械 (14)
    "1504",  # 東元
    "2609",  # 陽明海運
    "2615",  # 萬海
    "2603",  # 長榮海運
    "2610",  # 華航
]


def load_company_list(filter_ids: list[str] | None = None, industry_code: str | None = None) -> list[dict]:
    """從 companies.json 讀取公司資料，可按 id 或產業過濾"""
    with open(COMPANIES_JSON, encoding="utf-8") as f:
        raw = json.load(f)

    companies = []
    for item in raw:
        cid = str(item.get("公司代號", "")).strip()
        if not cid:
            continue
        if filter_ids and cid not in filter_ids:
            continue
        if industry_code and str(item.get("產業別", "")).strip() != industry_code:
            continue
        companies.append({
            "company_id": cid,
            "short_name": item.get("公司簡稱", ""),
            "full_name": item.get("公司名稱", ""),
            "industry_code": str(item.get("產業別", "")).strip(),
            "industry_name": "",  # 可後續補充產業名稱對照表
            "en_name": item.get("英文簡稱", ""),
        })
    return companies


def run_etl(
    company_ids: list[str] | None = None,
    industry_code: str | None = None,
    start_year: int = 2022,
    end_year: int = 2025,
    dry_run: bool = False,
) -> None:
    """
    主 ETL 流程：
    1. 載入公司清單
    2. 初始化 DB schema
    3. 迴圈：每家公司 × 每個可用季度 → 拉資料 → 清洗 → 寫入
    4. 記錄 etl_run
    """
    # 初始化 DB
    if not dry_run:
        Base.metadata.create_all(bind=engine)

    # 載入公司
    filter_ids = company_ids or PRIORITY_COMPANIES
    companies = load_company_list(filter_ids=filter_ids, industry_code=industry_code)
    if not companies:
        print("[ETL] 找不到符合條件的公司，結束。")
        return

    periods = available_periods(start_year, end_year)
    print(f"[ETL] 公司數：{len(companies)}，可用季度：{len(periods)}")
    print(f"[ETL] 季度範圍：{periods[0]} ~ {periods[-1]}")

    session = SessionLocal()
    run_id: int | None = None
    total_rows = 0
    companies_done = 0

    try:
        if not dry_run:
            run_id = create_etl_run(session, notes=f"companies={len(companies)}, periods={len(periods)}")

        # 先 upsert 公司基本資料
        for co in companies:
            if not dry_run:
                upsert_company(session, co)
        if not dry_run:
            session.commit()

        # 迴圈拉資料
        for co in companies:
            cid = co["company_id"]
            name = co["short_name"]
            print(f"\n[{cid}] {name}")
            companies_done += 1

            # 存前期 metrics 供 YoY 計算
            metrics_cache: dict[tuple, dict] = {}

            for year, season in periods:
                print(f"  → {year} Q{season} ", end="", flush=True)
                try:
                    stmts = fetch_all_statements(cid, year, season)

                    bs = parse_statement_rows(
                        (stmts.get("balance") or {}).get("reportList", []), "balance"
                    )
                    inc = parse_statement_rows(
                        (stmts.get("income") or {}).get("reportList", []), "income"
                    )
                    cf = parse_statement_rows(
                        (stmts.get("cash_flow") or {}).get("reportList", []), "cash_flow"
                    )

                    metrics = compute_metrics(bs, inc, cf)

                    # YoY：用一年前同期
                    year_ago_key = (year - 1, season)
                    if year_ago_key in metrics_cache:
                        yoy = compute_yoy(metrics, metrics_cache[year_ago_key])
                        metrics.update(yoy)

                    metrics_cache[(year, season)] = metrics

                    if not dry_run:
                        upsert_statements(session, cid, year, season, "balance", bs)
                        upsert_statements(session, cid, year, season, "income", inc)
                        upsert_statements(session, cid, year, season, "cash_flow", cf)
                        upsert_metrics(session, cid, year, season, metrics)
                        session.commit()

                    total_rows += len(bs) + len(inc) + len(cf)
                    print("✓")

                except ValueError as e:
                    print(f"SKIP ({e})")
                except Exception as e:
                    print(f"ERROR: {e}")
                    traceback.print_exc()

        # 完成 ETL run
        if not dry_run and run_id:
            finish_etl_run(
                session, run_id,
                companies_processed=companies_done,
                rows_upserted=total_rows,
                status="success",
            )

        print(f"\n[ETL] 完成！公司 {companies_done} 家，行數 {total_rows}。")

    except Exception as e:
        print(f"\n[ETL] 嚴重錯誤：{e}")
        traceback.print_exc()
        if not dry_run and run_id:
            finish_etl_run(
                session, run_id,
                companies_processed=companies_done,
                rows_upserted=total_rows,
                status="error",
                notes=str(e),
            )
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="tw-finscope ETL runner")
    parser.add_argument("--companies", nargs="*", help="公司代號清單（空格分隔）")
    parser.add_argument("--industry", help="產業別代碼（如 08）")
    parser.add_argument("--all", action="store_true", help="跑全部公司")
    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--dry-run", action="store_true", help="不寫入 DB，只印出")
    args = parser.parse_args()

    company_ids = None
    if args.companies:
        company_ids = args.companies
    elif not args.all:
        company_ids = PRIORITY_COMPANIES  # 預設跑 40 家代表性公司

    run_etl(
        company_ids=company_ids,
        industry_code=args.industry,
        start_year=args.start_year,
        end_year=args.end_year,
        dry_run=args.dry_run,
    )
