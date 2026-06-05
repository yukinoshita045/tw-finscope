"""
extract.py — MOPS 公開資訊觀測站 HTTP client
Python port of twse-finance-mcp/src/lib.ts

Usage:
    from pipeline.extract import fetch_balance, fetch_income_statement, fetch_cash_flow
"""

import time
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

MOPS_API_BASE = "https://mops.twse.com.tw/mops/api"
MOPS_WEB_BASE = "https://mops.twse.com.tw/mops/web"

BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://mops.twse.com.tw",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}

# 每次 API 請求之間最小間隔（秒），避免被 MOPS 封鎖
REQUEST_DELAY_SEC = 1.2
_last_request_time: float = 0.0


def _rate_limit() -> None:
    """確保請求間隔 >= REQUEST_DELAY_SEC"""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < REQUEST_DELAY_SEC:
        time.sleep(REQUEST_DELAY_SEC - elapsed)
    _last_request_time = time.monotonic()


def roc_to_gregorian(year: str | int) -> int:
    """民國年 → 西元年。可接受 3~4 位數字串或整數。"""
    y = int(str(year).strip())
    if y > 1911:
        return y  # 已是西元年，直接回傳
    return y + 1911


def gregorian_to_roc(year: int) -> str:
    """西元年 → 民國年字串"""
    return str(year - 1911)


# 各季度的揭露截止日（台北時區）
_DEADLINE_MAP: dict[int, tuple[int, int]] = {
    1: (5, 15),
    2: (8, 14),
    3: (11, 14),
    4: (3, 31),  # 次年
}


def is_undisclosed(roc_year: int, season: int, today: date | None = None) -> bool:
    """判斷某季度財報是否尚未揭露（截止日尚未到達）"""
    if today is None:
        today = datetime.now(tz=ZoneInfo("Asia/Taipei")).date()

    gregorian_year = roc_year + 1911
    month, day = _DEADLINE_MAP[season]
    # Q4 截止在次年
    deadline_year = gregorian_year + 1 if season == 4 else gregorian_year
    deadline = date(deadline_year, month, day)
    return today <= deadline


def available_periods(start_year: int = 2022, end_year: int = 2025) -> list[tuple[int, int]]:
    """
    回傳從 start_year Q1 到目前已揭露的所有 (gregorian_year, season) 組合
    """
    today = datetime.now(tz=ZoneInfo("Asia/Taipei")).date()
    periods = []
    for y in range(start_year, end_year + 1):
        for s in range(1, 5):
            roc_y = y - 1911
            if not is_undisclosed(roc_y, s, today):
                periods.append((y, s))
    return periods


def _check_security_block(data: Any) -> None:
    if isinstance(data, str) and "THE PAGE CANNOT BE ACCESSED" in data:
        raise RuntimeError(
            "MOPS blocked this request (security page). "
            "Please check headers: Origin, Referer, User-Agent."
        )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_statement(endpoint: str, referer_path: str, payload: dict) -> dict:
    """
    通用財報拉取函式（帶 retry）
    回傳格式: { "titles": [...], "reportList": [...] }
    """
    _rate_limit()
    url = f"{MOPS_API_BASE}/{endpoint}"
    headers = {
        **BASE_HEADERS,
        "Referer": f"{MOPS_WEB_BASE}/{referer_path}",
    }

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

    data = resp.json()
    _check_security_block(data)

    # MOPS 回傳 code/message 表示錯誤
    if data.get("result") is None:
        code = data.get("code")
        msg = data.get("message", "")
        if code == 406 or "查無" in msg or "無資料" in msg:
            raise ValueError(f"MOPS: no data (code={code}, message={msg})")
        raise RuntimeError(f"MOPS API error (code={code}, message={msg})")

    return data["result"]  # { "titles": [...], "reportList": [...] }


def _build_payload(company_id: str, roc_year: int, season: int, data_type: str = "2") -> dict:
    return {
        "companyId": str(company_id),
        "dataType": data_type,
        "season": str(season),
        "year": str(roc_year),
        "subsidiaryCompanyId": "",
    }


def fetch_balance(company_id: str, gregorian_year: int, season: int) -> dict:
    """
    拉取資產負債表
    :return: { "titles": [...], "reportList": [...] }
    """
    roc_year = gregorian_year - 1911
    if is_undisclosed(roc_year, season):
        raise ValueError(f"Balance sheet for {gregorian_year} Q{season} not yet disclosed.")
    payload = _build_payload(company_id, roc_year, season)
    return _fetch_statement("t164sb03", "t164sb03", payload)


def fetch_income_statement(company_id: str, gregorian_year: int, season: int) -> dict:
    """拉取綜合損益表"""
    roc_year = gregorian_year - 1911
    if is_undisclosed(roc_year, season):
        raise ValueError(f"Income statement for {gregorian_year} Q{season} not yet disclosed.")
    payload = _build_payload(company_id, roc_year, season)
    return _fetch_statement("t164sb04", "t164sb04", payload)


def fetch_cash_flow(company_id: str, gregorian_year: int, season: int) -> dict:
    """拉取現金流量表"""
    roc_year = gregorian_year - 1911
    if is_undisclosed(roc_year, season):
        raise ValueError(f"Cash flow for {gregorian_year} Q{season} not yet disclosed.")
    payload = _build_payload(company_id, roc_year, season)
    return _fetch_statement("t164sb05", "t164sb05", payload)


def fetch_all_statements(company_id: str, gregorian_year: int, season: int) -> dict:
    """
    一次拉取三份報表，回傳 dict
    keys: "balance", "income", "cash_flow"
    """
    result = {}
    for stmt_type, fetcher in [
        ("balance", fetch_balance),
        ("income", fetch_income_statement),
        ("cash_flow", fetch_cash_flow),
    ]:
        try:
            result[stmt_type] = fetcher(company_id, gregorian_year, season)
        except ValueError as e:
            print(f"  [SKIP] {company_id} {gregorian_year}Q{season} {stmt_type}: {e}")
            result[stmt_type] = None
        except Exception as e:
            print(f"  [ERROR] {company_id} {gregorian_year}Q{season} {stmt_type}: {e}")
            result[stmt_type] = None
    return result


# ── 快速測試 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    print("Testing TSMC (2330) 2024 Q3 income statement...")
    try:
        result = fetch_income_statement("2330", 2024, 3)
        print(f"  titles: {result['titles']}")
        print(f"  rows: {len(result['reportList'])}")
        print(f"  first row: {json.dumps(result['reportList'][0], ensure_ascii=False)}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\nAvailable periods (2023–2025):")
    for p in available_periods(2023, 2025):
        print(f"  {p[0]} Q{p[1]}")
