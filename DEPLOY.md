# tw-finscope 部署指南

把專案搬到網路上,讓老師可以打開公開網址做 demo。
全程使用免費方案,不需要自有網域。

---

## 總覽:三個服務,一個流程

```
GitHub (原始碼)
    │  git push
    ▼
┌──────────────┐    ┌──────────────┐    ┌───────────────┐
│  Render      │    │  Render      │    │   Vercel      │
│  PostgreSQL  │←───│  FastAPI     │←───│   React       │
│  (免費)       │    │  (免費)       │    │   (免費)       │
└──────────────┘    └──────────────┘    └───────────────┘
       ▲                                       │
       │           GitHub Actions              │ 公開 URL
       └─── 每週一定時 ETL ──────┐              ▼
                                                
```

需要的帳號(都免費,Gmail/GitHub 登入即可):
- GitHub
- Render (https://render.com)
- Vercel (https://vercel.com)

---

## Step 0 — 本地先確認能跑(可選)

如果你想先在自己電腦試一輪,確認沒問題再上雲端:

```bash
cd tw-finscope
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 沒有 Postgres? 預設用 SQLite,直接灌示範資料:
python -m pipeline.seed_demo

# 啟動 API
python -m uvicorn backend.main:app --reload --port 8000
# 開瀏覽器看 http://localhost:8000/docs

# 另開一個 terminal,跑前端
cd frontend
npm install
npm run dev
# 開 http://localhost:5173
```

確認 dashboard 能跑就可以開始部署。

---

## Step 1 — 推上 GitHub

### 1.1 在 GitHub 建立新 repo

1. 開 https://github.com/new
2. Repository name 填 `tw-finscope`
3. 選 **Public**(這樣 Render / Vercel 免費方案才能用)
4. **不要**勾 "Add a README" 或 "Add .gitignore"(本地已經有了)
5. 點 **Create repository**

GitHub 會給你一段指令,先收著。

### 1.2 在本地把 tw-finscope 推上去

```bash
cd tw-finscope                    # 必須在 tw-finscope/ 目錄下,而不是上一層
git init
git add .
git commit -m "Initial commit: tw-finscope dashboard"
git branch -M main
git remote add origin https://github.com/<你的帳號>/tw-finscope.git
git push -u origin main
```

> 為何不從上一層 `視覺化與現代資料科學/` push?
> 因為 Render / Vercel 預期 repo 根就是專案根。
> 把 `tw-finscope/` 當 repo root 最直觀。

推完後刷新 GitHub 頁面,應該看到所有檔案,包括 `.github/workflows/etl.yml`。

---

## Step 2 — 部署資料庫 + 後端到 Render

Render 可以「一個 yaml 一鍵生 Postgres + Web Service」。我已經寫好 `render.yaml`。

### 2.1 註冊 Render

1. 開 https://render.com,點 Sign Up,用 GitHub 登入
2. 第一次登入會問要不要安裝 Render GitHub App,選擇「Only select repositories」→ 選 `tw-finscope`

### 2.2 用 Blueprint 一鍵建立

1. Dashboard 左側點 **Blueprints** → **New Blueprint Instance**
2. 選你剛 push 的 `tw-finscope` repo,Branch 選 `main`
3. Render 會自動偵測 `render.yaml`,顯示要建立:
   - `tw-finscope-api`(Web Service, Python)
   - `tw-finscope-db`(PostgreSQL)
4. 點 **Apply**,等 3-5 分鐘讓兩個服務都變綠燈
5. 點 `tw-finscope-api`,複製上方那個網址(類似 `https://tw-finscope-api.onrender.com`)— **這是你的後端 URL,記下來**

### 2.3 設定 CORS 環境變數(暫時跳過,等前端網址出來再填)

---

## Step 3 — 部署前端到 Vercel

### 3.1 註冊 Vercel

1. 開 https://vercel.com,用 GitHub 登入
2. 同樣選擇允許 `tw-finscope` repo

### 3.2 Import Project

1. Dashboard 點 **Add New** → **Project**
2. 選 `tw-finscope` repo,**Root Directory** 改成 `frontend`(很重要!)
3. Framework Preset 應該自動辨識成 **Vite**
4. 展開 **Environment Variables**,新增一個:
   - Name: `VITE_API_BASE`
   - Value: `https://tw-finscope-api.onrender.com`(剛剛 Render 給你的網址)
5. 點 **Deploy**,等 2-3 分鐘
6. 部署完成後會給一個 `https://tw-finscope.vercel.app` — **這是 demo 用的網址**

### 3.3 回 Render 設 CORS

回 Render → `tw-finscope-api` → 左側 **Environment** → **Add Environment Variable**:
- Key: `CORS_ORIGIN`
- Value: `https://tw-finscope.vercel.app`

按 **Save Changes**,Render 會自動重新部署一次(約 1-2 分鐘)。

---

## Step 4 — 初次資料載入(灌 demo 資料,讓 dashboard 不是空的)

### 方案 A:用 Render Shell(快,推薦給 demo)

1. Render → `tw-finscope-api` → 左側 **Shell**
2. 輸入:
   ```bash
   python -m pipeline.seed_demo
   ```
3. 應該看到 `[seed] 完成。公司 8 家...` 的訊息

打開你的 Vercel 網址,dashboard 已經有資料可以看了。

### 方案 B:用 GitHub Actions 跑真實 MOPS 資料

(放心,即使這步出錯,seed_demo 也已經先讓 demo 能跑了)

1. 進 Render `tw-finscope-db` → **Info** → 複製 **Internal Database URL**(以 `postgresql://` 開頭那段)
2. 回 GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   - Name: `DATABASE_URL`
   - Value: 貼上剛複製的 URL
3. 進 GitHub repo → **Actions** 分頁 → 左側 **Weekly ETL Refresh** → **Run workflow** → 直接按 **Run workflow**
4. 跑完(約 5-15 分鐘,取決於選了多少家公司),dashboard 就會看到真實 MOPS 資料

> 注意:如果你想讓**自動排程**也跑起來,GitHub Actions 預設會在每週一台北時間早上 10:00 自動觸發,你不用做任何事。

---

## Step 5 — Demo 前最後檢查清單

Demo 前 5 分鐘:

- [ ] 打開 Vercel 網址 → 看到資料、圖表正常
- [ ] 切換公司(下拉選不同公司)→ 圖會更新
- [ ] 切換產業 → 公司清單會過濾
- [ ] 切換指標 tab(營收/淨利/毛利)→ 趨勢線會更新
- [ ] 「產業平均疊圖」勾選 → 出現灰色虛線
- [ ] 排名表切換指標 → 排名重新計算
- [ ] 右上角「資料更新」徽章顯示時間
- [ ] GitHub repo 的 Actions 分頁:準備好給老師看排程歷史

> Render 免費方案閒置 15 分鐘會休眠,demo 前 3-5 分鐘先打開網址讓它暖機!

---

## 常見問題排除

**Q: 打開 Vercel 網址,圖表空空、Console 顯示 CORS 錯誤?**
A: Step 3.3 沒做。回 Render 把 `CORS_ORIGIN` 設好,等重新部署完。

**Q: API 502 或非常慢?**
A: Render 免費 Web Service 閒置 15 分會睡。第一次打開要等 30-60 秒喚醒。Demo 前先暖機。

**Q: dashboard 顯示「尚無 ETL 記錄」?**
A: Step 4 沒做。回 Render Shell 跑 `python -m pipeline.seed_demo`(最快)或從 GitHub Actions 手動觸發 ETL。

**Q: MOPS 抓資料時被擋?**
A: 正常,MOPS 偶爾會阻擋。`pipeline/extract.py` 已經設好 retry。如果一直擋,改用 `seed_demo.py` 的合成資料 demo 也完全 OK,因為流程一樣是 extract→transform→load。

**Q: 想換 Render Postgres 為 Supabase?**
A: 在 Supabase 開免費專案,複製 `Settings → Database → Connection string → URI`,
然後在 Render 把 `DATABASE_URL` 環境變數從「fromDatabase」改成手動填這串。

**Q: GitHub Actions 失敗?**
A: 通常是 `DATABASE_URL` secret 沒設,或網址寫成 Internal URL 但 Actions 在 GitHub 跑要用 External URL。回 Render → DB → Info → 複製 **External Database URL**。

---

## 你的最終交付網址

- **Frontend (demo URL):** `https://tw-finscope.vercel.app`
- **Backend API:** `https://tw-finscope-api.onrender.com/docs`(FastAPI 自動產生的 Swagger 文件)
- **GitHub repo:** `https://github.com/yukinoshita045/tw-finscope`
- **GitHub Actions:** `https://github.com/yukinoshita045/tw-finscope/actions`(展示 ETL 自動排程)
