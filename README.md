# tw-finscope — Taiwan Listed-Company Financial Health Dashboard

台灣上市公司財務健康儀表板，自動從 MOPS 公開資訊觀測站拉取財報、跑 ETL，透過 FastAPI 提供 JSON API，React + Chart.js 呈現互動圖表。

## 快速開始

### 1. 安裝 Python 依賴

```bash
cd tw-finscope
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入 DATABASE_URL
```

### 3. 啟動本地 PostgreSQL（Docker）

```bash
docker run -d --name tw-finscope-db \
  -e POSTGRES_DB=twfinscope \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:16
```

### 4. 執行 ETL（初始 backfill）

```bash
# 跑預設 40 家代表性公司，2022-2025 年
python -m pipeline.run_etl

# 只跑台積電和聯發科，快速測試
python -m pipeline.run_etl --companies 2330 2454 --start-year 2024 --end-year 2025
```

### 5. 啟動 FastAPI

```bash
uvicorn backend.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 6. 啟動前端

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

## 部署

見 `EXEC_SUMMARY.md` 和 `PROJECT_PLAN.md` 第 8 節。

## 專案結構

```
tw-finscope/
├── pipeline/       ETL（extract → transform → load）
├── backend/        FastAPI + SQLAlchemy
├── frontend/       React + Chart.js (Vite)
├── .github/        GitHub Actions ETL 排程
└── EXEC_SUMMARY.md 執行摘要（期末報告用）
```
