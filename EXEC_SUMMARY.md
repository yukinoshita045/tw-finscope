# Taiwan Listed-Company Financial Health Dashboard

**Project:** tw-finscope  ·  **Live:** `https://tw-finscope-xxx.vercel.app`  ·  **Repo:** `https://github.com/<you>/tw-finscope`

---

## 一、問題與動機

台灣公開資訊觀測站(MOPS)公開了所有上市公司財報,但資料分散在三種報表(資產負債/損益/現金流量)、欄位以中文命名、日期為民國紀年、金額為字串並含全形破折號與括號負數,使一般使用者難以快速比較公司財務體質。**tw-finscope** 自動拉取並標準化這三份報表、計算十項衍生指標、寫入資料庫,以互動儀表板呈現,讓使用者無需下載任何資料即可比較不同公司與產業。

## 二、資料工程亮點

**E 抽取:** Python `httpx` 呼叫 MOPS 三個 endpoint(`t164sb03/04/05`),帶 browser-like headers 通過防爬,`tenacity` 三次指數回退重試,請求間 1.2 秒節流。

**T 轉換:** (1) 民國年↔西元年雙向轉換;(2) 中文科目 → canonical key(`line_items.py`,涵蓋 BS/IS/CF 共 60+ 對應);(3) 字串清洗——千分位逗號、全形空白、括號表負、`－` 表 NA;(4) **計算 10 項衍生指標**——毛利率/營業利益率/淨利率、ROE、ROA、流動比率、負債比率、營業 FCF、營收 YoY、淨利 YoY;(5) 三個衡量百分比的指標自動偵測是否需要 ×100 標準化。

**L 載入:** `ON CONFLICT DO UPDATE` 對 `(company_id, year, season, statement_type, line_item_key)` 與 `(company_id, year, season)` 做冪等 upsert——任何時候重跑都不會產生重複列。Schema 分三層:`statements`(長表原始) → `metrics`(寬表黃金) → `etl_runs`(可追溯)。

**規模:** 預設 40 家公司 × 16 季 = 640 個期間 × 3 份報表 ≈ 2,500 筆指標列。

## 三、視覺化

四種互補的圖表類型,全程互動:

1. **損益趨勢線圖**——多公司營收/毛利/淨利時序對比,可疊加同產業平均(虛線)做基準
2. **利潤率分組長條圖**——毛利率/營業利益率/淨利率三層分解,看「賺錢的品質」
3. **財務比率雷達圖**——5 維(毛利率/營業利益率/淨利率/ROE/ROA)跨公司一眼比較體質
4. **產業排名表**——9 種指標自由切換,可按產業過濾,顯示前 25 名
5. **財務健康分數卡(複合創新指標)**——把 5 項比率加權成 0–100 單一分數:毛利率(30%)+ ROE(25%)+ 流動比率(20%)+ 低負債(15%)+ 營收成長(10%);分數依區間以顏色(綠/藍/橘/紅)即時呈現,讓非財務背景使用者立即理解。

## 四、資料更新機制

`.github/workflows/etl.yml`:cron 每週一台北時間 10:00 自動執行 ETL,寫入 Postgres,同時支援 `workflow_dispatch` 手動觸發(可選擇公司清單和年份)。`etl_runs` 表記錄每次起訖、處理公司數、寫入列數、狀態與註記,構成完整 data lineage。儀表板右上角的「資料更新」徽章直接讀此表,使用者隨時知道資料新鮮度。

## 五、系統架構

```
GitHub Actions(每週/手動)→ Python ETL(extract → transform → load)
                                       → PostgreSQL(Render)
                                              ↓
                                       FastAPI(Render):/api/companies,
                                       /timeseries, /industry-average, /ranking, /meta
                                              ↓ JSON + CORS
                                       React + Chart.js(Vercel)
```

## 六、技術棧

**Back-end:** Python 3.12 · FastAPI · SQLAlchemy 2 · httpx · tenacity
**Front-end:** React 18 · Vite · Chart.js + react-chartjs-2
**Database:** PostgreSQL 16(生產) / SQLite(本地與離線 demo)
**DevOps:** GitHub Actions · Render(API + DB) · Vercel(前端)
