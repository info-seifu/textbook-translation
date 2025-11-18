"""
FastAPI メインアプリケーション
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.api import upload, translate, status, download, batch_translate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時の処理
    print("🚀 Starting Textbook Translation API...")

    # アップロードディレクトリの作成
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    yield

    # 終了時の処理
    print("👋 Shutting down Textbook Translation API...")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Textbook Translation API",
    description="Google Gemini APIを活用した教科書翻訳システム",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ========== WebUI Routes ==========

@app.get("/")
async def index(request: Request):
    """トップページ"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/upload")
async def upload_page(request: Request):
    """アップロードページ"""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/status/{job_id}")
async def status_page(request: Request, job_id: str):
    """ステータスページ"""
    return templates.TemplateResponse(
        "status.html",
        {"request": request, "job_id": job_id}
    )


# ========== API Routes ==========

@app.get("/api")
async def api_root():
    """API ルートエンドポイント"""
    return {
        "message": "Textbook Translation API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
        "claude_api_configured": bool(settings.CLAUDE_API_KEY),
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)
    }


# APIルーターの登録
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(batch_translate.router, prefix="/api", tags=["batch-translate"])
app.include_router(status.router, prefix="/api", tags=["status"])
app.include_router(download.router, prefix="/api", tags=["download"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
