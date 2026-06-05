"""
main.py — FastAPI 應用程式主入口
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import engine
from backend.models import Base
from backend.routers import companies, meta, metrics

# 啟動時自動建立所有 DB 表（若尚未存在）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="tw-finscope API",
    description="Taiwan Listed-Company Financial Health Dashboard API",
    version="1.0.0",
)

# CORS 設定
ALLOWED_ORIGINS = [
    "http://localhost:5173",       # Vite dev server
    "http://localhost:3000",
]
# 透過環境變數擴充(逗號分隔多個 origin),如:
#   CORS_ORIGIN=https://myapp.vercel.app,https://staging.vercel.app
# Vercel 預設網址會被下方 regex 自動匹配,不必逐一列出
extra_origin = os.getenv("CORS_ORIGIN")
if extra_origin:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origin.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 routers
app.include_router(companies.router)
app.include_router(metrics.router)
app.include_router(meta.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
