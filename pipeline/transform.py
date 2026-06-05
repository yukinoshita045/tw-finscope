"""
transform.py — 清洗 MOPS 回傳資料，計算衍生指標

主要功能：
  1. parse_statement_rows()   — 把 reportList 轉成 {key: value} dict
  2. compute_metrics()        — 從三份報表計算所有財務指標
  3. compute_yoy()            — 計算 YoY 成長率（需同公司前四季資料）
"""

from typing import Any

from pipeline.line_items import normalize_label


def _parse_number(raw: Any) -> float | None:
    """
    將 MOPS 回傳的字串數值轉為 float
    例："1,234,567" → 1234567.0
        "(123,456)" → -123456.0  (括號表示負數)
        "－" or "" → None
    """
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace(" ", "")
    if not s or s in ("－", "-", "—", "N/A", "n/a"):
        return None
    # 括號負數
    if s.startswith("(") and s.endswith(")"):
        inner = s[1:-1].replace(",", "")
        try:
            return -float(inner)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_statement_rows(report_list: list[dict], stmt_type: str) -> dict[str, float | None]:
    """
    將 MOPS reportList 轉換為 {canonical_key: float | None}
    :param report_list: MOPS API 回傳的 reportList
    :param stmt_type: "balance" | "income" | "cash_flow"
    :return: dict of {canonical_key: value}
    """
    result: dict[str, float | None] = {}
    if not report_list:
        return result

    for row in report_list:
        # MOPS 行格式通常是：科目名稱欄 + 金額欄（可能有多欄）
        # 科目名稱欄的 key 通常包含「科目」或是第一欄
        label: str | None = None
        value_raw: Any = None

        for col_key, col_val in row.items():
            col_key_str = str(col_key)
            if "科目" in col_key_str or col_key_str in ("項目", "name", "label"):
                label = str(col_val).strip() if col_val is not None else None
            elif "金額" in col_key_str or "當期" in col_key_str or "本期" in col_key_str:
                value_raw = col_val

        # 若無明確科目欄，取第一欄作為 label、最後一欄作為 value
        if label is None:
            cols = list(row.items())
            if cols:
                label = str(cols[0][1]).strip() if cols[0][1] is not None else None
            if len(cols) >= 2:
                # 取最後一個有值的非科目欄
                for _, v in reversed(cols[1:]):
                    if v is not None and str(v).strip():
                        value_raw = v
                        break

        if not label:
            continue

        key = normalize_label(label, stmt_type)
        if key is None:
            continue

        value = _parse_number(value_raw)
        # 若已有值（可能有重複 key），保留第一個非 None
        if key not in result or result[key] is None:
            result[key] = value

    return result


def compute_metrics(
    balance: dict[str, float | None],
    income: dict[str, float | None],
    cash_flow: dict[str, float | None],
) -> dict[str, float | None]:
    """
    從三份報表的 canonical key dict 計算所有衍生財務指標
    """
    def safe_div(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or b == 0:
            return None
        return a / b

    rev = income.get("revenue")
    gross = income.get("gross_profit")
    op_inc = income.get("operating_income")
    net = income.get("net_income") or income.get("net_income_attributable")
    total_assets = balance.get("total_assets")
    total_eq = balance.get("total_equity") or balance.get("equity_attributable_to_parent")
    total_liab = balance.get("total_liabilities")
    curr_assets = balance.get("total_current_assets")
    curr_liab = balance.get("total_current_liabilities")
    op_cf = cash_flow.get("operating_cash_flow")

    metrics: dict[str, float | None] = {
        # 基本損益
        "revenue": rev,
        "gross_profit": gross,
        "operating_income": op_inc,
        "net_income": net,
        # 資產負債
        "total_assets": total_assets,
        "total_equity": total_eq,
        "total_liabilities": total_liab,
        "current_assets": curr_assets,
        "current_liabilities": curr_liab,
        "operating_cash_flow": op_cf,
        # EPS
        "eps_basic": income.get("eps_basic"),
        "eps_diluted": income.get("eps_diluted"),
        # 利潤率 (%)
        "gross_margin": safe_div(gross, rev),
        "operating_margin": safe_div(op_inc, rev),
        "net_margin": safe_div(net, rev),
        # 報酬率 (%)
        "roe": safe_div(net, total_eq),
        "roa": safe_div(net, total_assets),
        # 流動比率、負債比率
        "current_ratio": safe_div(curr_assets, curr_liab),
        "debt_ratio": safe_div(total_liab, total_assets),
        # FCF（自由現金流量）= 營業 CF - capex
        "free_cash_flow": (
            (op_cf or 0) - abs(cash_flow.get("capex") or 0)
            if op_cf is not None else None
        ),
    }

    # 將百分率欄位正規化（若原始數值已是小數形式則 ×100，若 >1 則已是百分比）
    for pct_key in ("gross_margin", "operating_margin", "net_margin", "roe", "roa", "debt_ratio"):
        val = metrics[pct_key]
        if val is not None and abs(val) <= 10:  # 已是小數形式（e.g. 0.35）
            metrics[pct_key] = round(val * 100, 4)
        elif val is not None:
            metrics[pct_key] = round(val, 4)

    return metrics


def compute_yoy(
    current: dict[str, float | None],
    year_ago: dict[str, float | None],
) -> dict[str, float | None]:
    """
    計算 YoY 成長率（%）
    :param current: 本期 metrics dict
    :param year_ago: 一年前同期 metrics dict
    :return: {"revenue_yoy": ..., "net_income_yoy": ...}
    """
    yoy: dict[str, float | None] = {}
    for metric_key in ("revenue", "net_income", "operating_income"):
        curr_val = current.get(metric_key)
        prev_val = year_ago.get(metric_key)
        if curr_val is not None and prev_val is not None and prev_val != 0:
            yoy[f"{metric_key}_yoy"] = round((curr_val - prev_val) / abs(prev_val) * 100, 2)
        else:
            yoy[f"{metric_key}_yoy"] = None
    return yoy
