# セットアップガイド

## 必要な環境

- Python 3.10以上
- Node.js 18以上
- Supabaseアカウント
- Google Gemini APIキー
- Anthropic Claude APIキー

## 1. Supabaseのセットアップ

### 1.1 プロジェクト作成

1. [Supabase](https://supabase.com/)にアクセスしてプロジェクトを作成
2. プロジェクトURLとAPIキーをメモ

### 1.2 データベーススキーマの適用

1. Supabaseダッシュボードで「SQL Editor」を開く
2. `backend/database_schema.sql`の内容をコピー&ペースト
3. 実行して、テーブルとストレージバケットを作成

## 2. APIキーの取得

### 2.1 Google Gemini API

1. [Google AI Studio](https://makersuite.google.com/app/apikey)にアクセス
2. APIキーを作成

### 2.2 Anthropic Claude API

1. [Anthropic Console](https://console.anthropic.com/)にアクセス
2. APIキーを作成

## 3. バックエンドのセットアップ

### 3.1 仮想環境の作成

```bash
cd backend
python -m venv venv

# Windowsの場合
venv\Scripts\activate

# macOS/Linuxの場合
source venv/bin/activate
```

### 3.2 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3.3 環境変数の設定

`.env.example`を`.env`にコピーして編集:

```bash
cp .env.example .env
```

`.env`ファイルに以下を設定:

```bash
# Google Gemini
GEMINI_API_KEY=your_actual_gemini_api_key

# Anthropic Claude
CLAUDE_API_KEY=your_actual_claude_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# その他はデフォルトのまま
```

### 3.4 サーバー起動

```bash
# backend/ディレクトリから実行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

または

```bash
python -m app.main
```

ブラウザで `http://localhost:8000` にアクセスして確認。

## 4. フロントエンドのセットアップ

### 4.1 依存関係のインストール

```bash
cd frontend
npm install
```

### 4.2 環境変数の設定

`.env.local.example`を`.env.local`にコピーして編集:

```bash
cp .env.local.example .env.local
```

`.env.local`ファイルに以下を設定:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 4.3 開発サーバー起動

```bash
npm run dev
```

ブラウザで `http://localhost:3000` にアクセス。

## 5. 動作確認

### 5.1 バックエンドのヘルスチェック

```bash
curl http://localhost:8000/health
```

以下のようなレスポンスが返ってくれば成功:

```json
{
  "status": "healthy",
  "gemini_api_configured": true,
  "claude_api_configured": true,
  "supabase_configured": true
}
```

### 5.2 フロントエンド

ブラウザで `http://localhost:3000` を開き、トップページが表示されることを確認。

## 6. トラブルシューティング

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

### Supabase接続エラー

- URLとAPIキーが正しいか確認
- ネットワーク接続を確認
- Supabaseプロジェクトが起動しているか確認

### APIキーエラー

- `.env`ファイルが正しい場所にあるか確認
- APIキーに余分なスペースや改行がないか確認
- APIキーの有効期限を確認

## 7. 次のステップ

環境が整ったら、以下の順で実装を進めます：

1. Gemini OCRサービスの実装
2. Claude翻訳サービスの実装
3. APIエンドポイントの実装
4. フロントエンドUIの実装
5. 統合テスト

詳細は設計書 `docs/textbook-translation-app-design.md` を参照してください。
