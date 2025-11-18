# ============================================
# 教科書翻訳システム - Dockerfile
# ============================================
#
# このDockerfileは以下をサポートします:
# - ローカル開発環境
# - クラウドデプロイ (Fly.io, Oracle Cloud, VPS等)
# - WeasyPrintによるPDF生成

FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 環境変数の設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# システムパッケージの更新とWeasyPrint依存関係のインストール
# WeasyPrintにはCairo、Pango、GDK-PixBuf等が必要
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint依存関係
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # PDF2Image依存関係 (Poppler)
    poppler-utils \
    # 一般的なツール
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
# requirements.txtを先にコピーして、レイヤーキャッシュを活用
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# アップロードディレクトリを作成
RUN mkdir -p /app/uploads

# 非rootユーザーを作成して実行
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ポートを公開
EXPOSE 8000

# アプリケーション起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
