"""
line_items.py — 中文報表科目 → 標準英文 key 對應表

使用方式：
    from pipeline.line_items import BS_MAP, IS_MAP, CF_MAP, normalize_label
"""

# ── 資產負債表 (Balance Sheet) ─────────────────────────────────────────────────
BS_MAP: dict[str, str] = {
    # 流動資產
    "現金及約當現金": "cash_and_equivalents",
    "應收帳款": "accounts_receivable",
    "應收帳款淨額": "accounts_receivable",
    "存貨": "inventory",
    "流動資產合計": "total_current_assets",
    "流動資產": "total_current_assets",
    # 非流動資產
    "不動產廠房及設備": "ppe",
    "不動產、廠房及設備": "ppe",
    "無形資產": "intangible_assets",
    "長期投資": "long_term_investments",
    "非流動資產合計": "total_noncurrent_assets",
    "非流動資產": "total_noncurrent_assets",
    # 總資產
    "資產總計": "total_assets",
    "資產總額": "total_assets",
    # 流動負債
    "短期借款": "short_term_debt",
    "應付帳款": "accounts_payable",
    "流動負債合計": "total_current_liabilities",
    "流動負債": "total_current_liabilities",
    # 非流動負債
    "長期借款": "long_term_debt",
    "非流動負債合計": "total_noncurrent_liabilities",
    "非流動負債": "total_noncurrent_liabilities",
    # 總負債
    "負債總計": "total_liabilities",
    "負債總額": "total_liabilities",
    # 股東權益
    "股本": "share_capital",
    "保留盈餘": "retained_earnings",
    "歸屬於母公司業主之權益合計": "equity_attributable_to_parent",
    "歸屬於母公司業主之權益": "equity_attributable_to_parent",
    "非控制權益": "non_controlling_interest",
    "權益總計": "total_equity",
    "股東權益總計": "total_equity",
    "權益總額": "total_equity",
}

# ── 綜合損益表 (Income Statement) ─────────────────────────────────────────────
IS_MAP: dict[str, str] = {
    "營業收入合計": "revenue",
    "營業收入淨額": "revenue",
    "營業收入": "revenue",
    "營業成本合計": "cost_of_revenue",
    "營業成本": "cost_of_revenue",
    "營業毛利（毛損）": "gross_profit",
    "營業毛利": "gross_profit",
    "毛利": "gross_profit",
    "營業費用合計": "operating_expenses",
    "營業費用": "operating_expenses",
    "營業利益（損失）": "operating_income",
    "營業利益": "operating_income",
    "營業損益": "operating_income",
    "業外收入及支出": "non_operating_income",
    "稅前淨利（損失）": "income_before_tax",
    "繼續營業單位稅前淨利（損失）": "income_before_tax",
    "所得稅費用（利益）": "income_tax",
    "所得稅費用": "income_tax",
    "本期淨利（損失）": "net_income",
    "本期淨利": "net_income",
    "本期損益": "net_income",
    "歸屬於母公司業主之淨利（損失）": "net_income_attributable",
    "歸屬於母公司業主之淨利": "net_income_attributable",
    "其他綜合損益（稅後）": "other_comprehensive_income",
    "本期綜合損益總額": "total_comprehensive_income",
    "基本每股盈餘": "eps_basic",
    "稀釋每股盈餘": "eps_diluted",
}

# ── 現金流量表 (Cash Flow Statement) ─────────────────────────────────────────
CF_MAP: dict[str, str] = {
    "營業活動之現金流量": "operating_cash_flow",
    "來自（用於）營業活動之現金流量": "operating_cash_flow",
    "營業活動淨現金流入（流出）": "operating_cash_flow",
    "投資活動之現金流量": "investing_cash_flow",
    "投資活動淨現金流入（流出）": "investing_cash_flow",
    "籌資活動之現金流量": "financing_cash_flow",
    "籌資活動淨現金流入（流出）": "financing_cash_flow",
    "本期現金及約當現金增加（減少）數": "net_change_in_cash",
    "期末現金及約當現金": "ending_cash",
    "資本支出": "capex",
    "購置不動產廠房及設備": "capex",
    "購置不動產、廠房及設備": "capex",
}

# 所有 map 合集（用於快速查找）
ALL_MAPS = {
    "balance": BS_MAP,
    "income": IS_MAP,
    "cash_flow": CF_MAP,
}


def normalize_label(label: str, stmt_type: str) -> str | None:
    """
    將中文科目名稱轉換為標準英文 key
    :param label: 中文科目，如「營業收入合計」
    :param stmt_type: "balance" | "income" | "cash_flow"
    :return: 標準 key 或 None（若找不到對應）
    """
    mapping = ALL_MAPS.get(stmt_type, {})
    # 精確比對
    if label in mapping:
        return mapping[label]
    # 去除前後空白後再比對
    stripped = label.strip()
    if stripped in mapping:
        return mapping[stripped]
    # 嘗試部分比對（前綴）
    for zh_key, en_key in mapping.items():
        if stripped.startswith(zh_key) or zh_key.startswith(stripped):
            return en_key
    return None
