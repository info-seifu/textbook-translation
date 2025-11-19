# 本番環境デプロイメントガイド

このドキュメントでは、textbook-translationアプリケーションを本番環境にデプロイする方法を説明します。

## デプロイメント構成

### 推奨構成

1. **Backend**: Cloud Run / Railway / Render
2. **Frontend**: Vercel
3. **Database**: Supabase (PostgreSQL)
4. **Storage**: Supabase Storage

### 代替構成

- **All-in-one Docker**: Docker Compose (開発/ステージング環境向け)
- **Backend + Frontend**: Railway (シンプルな構成向け)

---

## 1. Supabaseセットアップ

### 1.1 プロジェクト作成

1. [Supabase](https://supabase.com/)にアクセスしてサインイン
2. "New Project"をクリック
3. プロジェクト名、データベースパスワードを設定
4. リージョンを選択（推奨: Asia Pacific (Tokyo)）

### 1.2 データベーステーブル作成

Supabase SQLエディタで以下を実行:

```sql
-- documentsテーブル
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_filename TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    page_count INTEGER,
    japanese_markdown_url TEXT,
    ocr_status TEXT NOT NULL DEFAULT 'pending',
    ocr_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- translationsテーブル
CREATE TABLE translations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_language TEXT NOT NULL,
    translator_engine TEXT NOT NULL,
    translated_markdown_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス作成
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_translations_job_id ON translations(job_id);
CREATE INDEX idx_translations_status ON translations(status);
```

### 1.3 Storageバケット作成

1. Supabase Dashboard → Storage
2. 以下の3つのバケットを作成:
   - `pdfs` - PDFファイル用
   - `documents` - Markdownファイル用
   - `figures` - 図解画像用
3. 各バケットのポリシー設定:
   - Public access: OFF（アプリケーションからのアクセスのみ）

### 1.4 環境変数取得

Supabase Dashboard → Settings → API から以下を取得:

- `SUPABASE_URL`: Project URL
- `SUPABASE_KEY`: Project API keys → `anon` `public`
- `SUPABASE_SERVICE_KEY`: Project API keys → `service_role` `secret`

---

## 2. Backendデプロイ (Cloud Run推奨)

### 2.1 前提条件

- Google Cloud アカウント
- gcloud CLI インストール

### 2.2 デプロイ手順

#### Dockerイメージ作成

```bash
cd backend

# イメージビルド
docker build -t gcr.io/YOUR_PROJECT_ID/textbook-translation-backend:latest .

# Google Container Registryにプッシュ
docker push gcr.io/YOUR_PROJECT_ID/textbook-translation-backend:latest
```

#### Cloud Runデプロイ

```bash
gcloud run deploy textbook-translation-backend \
  --image gcr.io/YOUR_PROJECT_ID/textbook-translation-backend:latest \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars "GEMINI_API_KEY=your_key" \
  --set-env-vars "CLAUDE_API_KEY=your_key" \
  --set-env-vars "SUPABASE_URL=your_url" \
  --set-env-vars "SUPABASE_KEY=your_key" \
  --set-env-vars "SUPABASE_SERVICE_KEY=your_service_key" \
  --set-env-vars "USE_GEMINI_3=false" \
  --set-env-vars "ALLOWED_ORIGINS=https://your-frontend.vercel.app"
```

#### 環境変数一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `GEMINI_API_KEY` | ✅ | Google Gemini APIキー |
| `CLAUDE_API_KEY` | ✅ | Anthropic Claude APIキー |
| `SUPABASE_URL` | ✅ | Supabase プロジェクトURL |
| `SUPABASE_KEY` | ✅ | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service role key |
| `USE_GEMINI_3` | ❌ | Gemini 3.0使用フラグ (デフォルト: false) |
| `ALLOWED_ORIGINS` | ❌ | CORS許可オリジン (カンマ区切り) |
| `MAX_FILE_SIZE_MB` | ❌ | 最大ファイルサイズ (デフォルト: 50) |

### 2.3 代替: Railway でのデプロイ

1. [Railway](https://railway.app/)にサインイン
2. "New Project" → "Deploy from GitHub repo"
3. リポジトリを選択
4. Root Directory: `backend`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Environment Variables を設定 (上記の環境変数一覧を参照)
7. Deploy

### 2.4 代替: Render でのデプロイ

1. [Render](https://render.com/)にサインイン
2. "New" → "Web Service"
3. リポジトリを接続
4. 設定:
   - Name: `textbook-translation-backend`
   - Runtime: `Docker`
   - Region: `Singapore`
   - Instance Type: `Standard`
5. Environment Variables を設定
6. "Create Web Service"

---

## 3. Frontendデプロイ (Vercel推奨)

### 3.1 前提条件

- Vercelアカウント
- GitHubリポジトリ連携

### 3.2 デプロイ手順

#### Vercel CLI使用

```bash
cd frontend

# Vercel CLIインストール (初回のみ)
npm install -g vercel

# デプロイ
vercel

# 本番デプロイ
vercel --prod
```

#### Vercel Dashboard使用

1. [Vercel](https://vercel.com/)にサインイン
2. "Add New..." → "Project"
3. GitHubリポジトリをインポート
4. 設定:
   - Framework Preset: `Next.js`
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`
5. Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.run.app
   ```
6. "Deploy"

### 3.3 環境変数設定

Vercel Dashboard → Settings → Environment Variables:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.run.app` | バックエンドURL |

### 3.4 カスタムドメイン設定 (オプション)

1. Vercel Dashboard → Settings → Domains
2. カスタムドメインを追加
3. DNSレコードを設定

---

## 4. Docker Composeデプロイ (開発/ステージング)

### 4.1 docker-compose.yml作成

プロジェクトルートに`docker-compose.yml`を作成:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - USE_GEMINI_3=false
      - ALLOWED_ORIGINS=http://localhost:3000
      - BACKEND_PORT=8000
      - BACKEND_HOST=0.0.0.0
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/storage:/app/storage
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped
```

### 4.2 デプロイ

```bash
# 環境変数ファイル作成
cp backend/.env.example .env
# .envファイルを編集

# ビルド & 起動
docker-compose up -d

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

---

## 5. デプロイ後の確認

### 5.1 バックエンド動作確認

```bash
# ヘルスチェック
curl https://your-backend.run.app/health

# 期待されるレスポンス
{"status":"healthy"}
```

### 5.2 フロントエンド動作確認

1. ブラウザで https://your-frontend.vercel.app にアクセス
2. PDFアップロード機能をテスト
3. OCR処理が正常に動作することを確認
4. 翻訳機能をテスト

### 5.3 Supabaseデータ確認

1. Supabase Dashboard → Table Editor
2. `documents`テーブルにレコードが作成されていることを確認
3. `translations`テーブルにレコードが作成されていることを確認

---

## 6. モニタリングとログ

### 6.1 Cloud Run

```bash
# ログ表示
gcloud run logs read textbook-translation-backend --limit 100

# メトリクス確認
gcloud run services describe textbook-translation-backend
```

### 6.2 Vercel

1. Vercel Dashboard → Deployments
2. 各デプロイメントのログを確認

### 6.3 Supabase

1. Supabase Dashboard → Database → Logs
2. Storage → Logs

---

## 7. トラブルシューティング

### 7.1 CORS エラー

**症状**: フロントエンドからバックエンドへのリクエストが失敗

**解決策**:
```bash
# バックエンドの環境変数を確認・更新
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://www.your-domain.com
```

### 7.2 ファイルアップロード失敗

**症状**: PDFアップロードが失敗する

**チェック項目**:
- Supabase Storageのバケットが作成されているか
- `SUPABASE_SERVICE_KEY`が正しく設定されているか
- ファイルサイズが`MAX_FILE_SIZE_MB`以下か

### 7.3 OCR/翻訳処理タイムアウト

**症状**: 処理が途中で停止する

**解決策**:
```bash
# Cloud Runのタイムアウトを延長
gcloud run services update textbook-translation-backend \
  --timeout 3600
```

### 7.4 Gemini API レート制限

**症状**: `429 Too Many Requests` エラー

**解決策**:
- `USE_GEMINI_3=true`に設定して有料版Gemini 3.0を使用
- リトライ処理が自動で実行されるまで待機

---

## 8. コスト見積もり

### 8.1 月間1000ページ処理の場合

| サービス | 項目 | コスト |
|---------|------|--------|
| **Gemini 2.5** | OCR (Pro): 1000ページ | ~$2-5 |
| **Gemini 2.5** | 翻訳 (Flash): 1000ページ | ~$1-3 |
| **Claude Sonnet** | 翻訳: 1000ページ | ~$10-20 |
| **Cloud Run** | 2vCPU, 2GB, 100時間/月 | ~$10 |
| **Vercel** | Hobby plan | $0 (Pro: $20) |
| **Supabase** | Free tier | $0 (Pro: $25) |
| **合計 (Gemini)** | | ~$13-18/月 |
| **合計 (Claude)** | | ~$22-35/月 |

### 8.2 コスト最適化

1. **OCR**: Gemini 2.5 Pro (無料枠内)
2. **翻訳**: Gemini 2.5 Flash (低コスト) → 高品質が必要な場合のみClaude
3. **インフラ**: Supabase Free tier (500MB DB, 1GB Storage)
4. **Frontend**: Vercel Hobby plan (個人利用)

---

## 9. セキュリティ

### 9.1 環境変数管理

- **本番環境**: Cloud Run/Vercel/Railw ayのシークレット管理機能を使用
- **ローカル**: `.env`ファイル (`.gitignore`で除外)

### 9.2 APIキー保護

- `SUPABASE_SERVICE_KEY`: サーバーサイドのみで使用
- `CLAUDE_API_KEY`, `GEMINI_API_KEY`: サーバーサイドのみで使用
- フロントエンドには公開しない

### 9.3 CORS設定

```python
# backend/app/main.py
ALLOWED_ORIGINS = [
    "https://your-frontend.vercel.app",
    "https://www.your-domain.com"
]
```

---

## 10. CI/CD (オプション)

### 10.1 GitHub Actions

`.github/workflows/deploy.yml`を作成:

```yaml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and Deploy to Cloud Run
        run: |
          gcloud run deploy textbook-translation-backend \
            --source ./backend \
            --region asia-northeast1

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
```

---

## サポート

問題が発生した場合は、以下を確認してください:

1. [README.md](../README.md) - 基本的なセットアップ
2. [設計書](./textbook-translation-app-design.md) - アーキテクチャ詳細
3. GitHub Issues - 既知の問題と解決策

---

**最終更新**: 2025-11-19
