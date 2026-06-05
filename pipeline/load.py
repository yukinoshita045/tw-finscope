"""
load.py — 將清洗後的資料 upsert 進 PostgreSQL

所有 upsert 都是 idempotent：重複執行不會產生重複資料。
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.models import Company, EtlRun, Metric, Statement


def upsert_company(session: Session, company_data: dict) -> None:
    """
    upsert 一筆公司資料
    company_data keys: company_id, short_name, full_name, industry_code, industry_name, en_name
    """
    stmt = text("""
        INSERT INTO companies (company_id, short_name, full_name, industry_code, industry_name, en_name)
        VALUES (:company_id, :short_name, :full_name, :industry_code, :industry_name, :en_name)
        ON CONFLICT (company_id) DO UPDATE SET
            short_name = EXCLUDED.short_name,
            full_name = EXCLUDED.full_name,
            industry_code = EXCLUDED.industry_code,
            industry_name = EXCLUDED.industry_name,
            en_name = EXCLUDED.en_name
    """)
    session.execute(stmt, company_data)


def upsert_statements(
    session: Session,
    company_id: str,
    year: int,
    season: int,
    stmt_type: str,
    rows: dict[str, float | None],
) -> int:
    """
    upsert 一份報表的所有 line items
    :return: upserted row count
    """
    count = 0
    for key, value in rows.items():
        if value is None:
            continue
        stmt = text("""
            INSERT INTO statements
                (company_id, year, season, statement_type, line_item_key, value)
            VALUES
                (:company_id, :year, :season, :statement_type, :line_item_key, :value)
            ON CONFLICT (company_id, year, season, statement_type, line_item_key) DO UPDATE SET
                value = EXCLUDED.value
        """)
        session.execute(stmt, {
            "company_id": company_id,
            "year": year,
            "season": season,
            "statement_type": stmt_type,
            "line_item_key": key,
            "value": value,
        })
        count += 1
    return count


def upsert_metrics(
    session: Session,
    company_id: str,
    year: int,
    season: int,
    metrics: dict[str, float | None],
) -> None:
    """
    upsert 衍生指標（metrics gold table）
    """
    # 建立欄位清單（只插入有值的欄位，但需列出所有可能欄位以組成 SQL）
    metric_cols = [
        "revenue", "gross_profit", "operating_income", "net_income",
        "total_assets", "total_equity", "total_liabilities",
        "current_assets", "current_liabilities", "operating_cash_flow",
        "eps_basic", "eps_diluted", "free_cash_flow",
        "gross_margin", "operating_margin", "net_margin",
        "roe", "roa", "current_ratio", "debt_ratio",
        "revenue_yoy", "net_income_yoy", "operating_income_yoy",
    ]
    col_clause = ", ".join(metric_cols)
    val_clause = ", ".join(f":{c}" for c in metric_cols)
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in metric_cols)

    params: dict = {
        "company_id": company_id,
        "year": year,
        "season": season,
    }
    for col in metric_cols:
        params[col] = metrics.get(col)  # None → NULL

    stmt = text(f"""
        INSERT INTO metrics
            (company_id, year, season, {col_clause})
        VALUES
            (:company_id, :year, :season, {val_clause})
        ON CONFLICT (company_id, year, season) DO UPDATE SET
            {update_clause}
    """)
    session.execute(stmt, params)


def create_etl_run(session: Session, notes: str = "") -> int:
    """開始一次 ETL run,回傳 run_id。

    用 ORM 物件以跨 Postgres / SQLite。
    (RETURNING + 手動 commit 在 SQLite 會有 cursor 未消耗問題。)
    """
    run = EtlRun(
        started_at=datetime.now(timezone.utc),
        status="running",
        notes=notes,
    )
    session.add(run)
    session.flush()    # 取得 autoincrement id
    session.commit()
    return run.id


def finish_etl_run(
    session: Session,
    run_id: int,
    companies_processed: int,
    rows_upserted: int,
    status: str = "success",
    notes: str = "",
) -> None:
    """完成一次 ETL run"""
    stmt = text("""
        UPDATE etl_runs
        SET finished_at = :finished_at,
            companies_processed = :companies_processed,
            rows_upserted = :rows_upserted,
            status = :status,
            notes = :notes
        WHERE id = :run_id
    """)
    session.execute(stmt, {
        "finished_at": datetime.now(timezone.utc),
        "companies_processed": companies_processed,
        "rows_upserted": rows_upserted,
        "status": status,
        "notes": notes,
        "run_id": run_id,
    })
    session.commit()
