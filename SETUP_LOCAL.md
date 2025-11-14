# ローカル環境セットアップガイド

このガイドでは、Supabaseを使わずにローカル環境のみで動作させる手順を説明します。

## 必要なもの

### 必須
- Python 3.10以上
- Node.js 18以上
- **Google Gemini APIキー**
- **Anthropic Claude APIキー**

### オプショナル（ローカル動作には不要）
- ~~Supabaseアカウント~~（ローカルではJSONファイルで代替）

## セットアップ手順

### 1. APIキーの取得

#### Google Gemini API
1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. APIキーを作成してコピー

#### Anthropic Claude API
1. [Anthropic Console](https://console.anthropic.com/)にアクセス
2. APIキーを作成してコピー

### 2. バックエンドのセットアップ

```bash
cd backend

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
```

`.env`ファイルを編集して、以下の2つのAPIキーのみ設定：

```bash
# Google Gemini API（必須）
GEMINI_API_KEY=あなたのGemini APIキー

# Anthropic Claude API（必須）
CLAUDE_API_KEY=あなたのClaude APIキー

# Supabase設定は空のままでOK
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=
```

### 3. バックエンドの起動

```bash
# backend/ディレクトリから実行
uvicorn app.main:app --reload
```

または

```bash
python -m app.main
```

起動したら `http://localhost:8000` にアクセスして確認。

### 4. フロントエンドのセットアップ（オプション）

```bash
cd ../frontend

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.local.example .env.local
```

`.env.local`ファイルを編集：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase設定は空のままでOK
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

### 5. フロントエンドの起動

```bash
npm run dev
```

`http://localhost:3000` にアクセス。

## 動作確認

### バックエンドのテスト

```bash
# ヘルスチェック
curl http://localhost:8000/health
```

期待される出力：
```json
{
  "status": "healthy",
  "gemini_api_configured": true,
  "claude_api_configured": true,
  "supabase_configured": false
}
```

**Note**: `supabase_configured`が`false`でも問題ありません。ローカルではJSONファイルを使用します。

### PDFアップロードのテスト

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@samples/pdf/horizontal/sample.pdf"
```

## データの保存場所

ローカル環境では以下のディレクトリにデータが保存されます：

```
backend/
├── storage/
│   ├── database.json          # ジョブ情報（JSONデータベース）
│   ├── pdfs/                  # アップロードされたPDF
│   ├── documents/             # マークダウンファイル
│   └── figures/               # 抽出された図解
└── uploads/                   # 一時アップロード
```

## トラブルシューティング

### pdf2imageのエラー

`pdf2image`は`poppler`に依存しています。

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
1. [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)をダウンロード
2. PATHに追加

### APIキーエラー

- `.env`ファイルが`backend/`ディレクトリにあるか確認
- APIキーに余分なスペースや改行がないか確認
- APIキーが有効か確認

### ポート衝突

別のアプリが8000ポートを使用している場合：

```bash
# .envファイルでポート変更
BACKEND_PORT=8001

# 起動
uvicorn app.main:app --reload --port 8001
```

## 使い方

### 1. PDFアップロード

フロントエンド: http://localhost:3000/upload

または

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@your-pdf-file.pdf"
```

レスポンス例：
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "OCR processing started"
}
```

### 2. ジョブステータス確認

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### 3. 翻訳開始

```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "target_language": "en",
    "translator_engine": "claude"
  }'
```

### 4. 結果ダウンロード

```bash
curl http://localhost:8000/api/download/{output_id}/markdown \
  -o translated.md
```

## 制限事項

ローカル環境での制限：

- ✅ 基本機能は全て動作
- ✅ PDFアップロード、OCR、翻訳
- ⚠️ ユーザー認証なし（全てのデータは共有）
- ⚠️ 同時アクセス制御が弱い
- ⚠️ データのバックアップなし

本番環境ではSupabaseの使用を推奨します。

## 次のステップ

動作確認ができたら：
1. サンプルPDFでテスト
2. Phase 2の機能追加（エンジン切り替え、複数言語対応など）
3. 必要に応じてSupabaseへの移行を検討
