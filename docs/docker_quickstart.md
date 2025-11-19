# Docker クイックスタートガイド

Docker Composeを使用して、textbook-translationアプリケーション全体をローカル環境または本番環境で簡単にデプロイできます。

## 前提条件

- Docker Desktop または Docker Engine + Docker Compose がインストールされていること
- Google Gemini APIキー
- Anthropic Claude APIキー

## セットアップ手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/info-seifu/textbook-translation.git
cd textbook-translation
```

### 2. 環境変数を設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# 必須項目:
# - GEMINI_API_KEY
# - CLAUDE_API_KEY
```

`.env`ファイルの例:

```env
# 必須
GEMINI_API_KEY=AIzaSy...your_gemini_key_here
CLAUDE_API_KEY=sk-ant-...your_claude_key_here

# オプション (本番環境のみ)
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=

# Gemini設定
USE_GEMINI_3=false

# ファイルアップロード設定
MAX_FILE_SIZE_MB=50

# フロントエンド設定
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Docker Composeで起動

```bash
# ビルドして起動
docker-compose up -d

# ログを確認
docker-compose logs -f
```

### 4. アプリケーションにアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

## 使用方法

### PDFアップロードと翻訳

1. ブラウザで http://localhost:3000 にアクセス
2. "PDFをアップロード"ボタンをクリック
3. 教科書のPDFファイルを選択
4. OCR処理が自動的に開始されます
5. OCR完了後、翻訳先言語と翻訳エンジンを選択
6. "翻訳を開始"ボタンをクリック
7. 翻訳完了後、Markdownファイルをダウンロード

### バックエンドWebUI使用 (代替方法)

バックエンドにはWebUIが組み込まれています:

1. http://localhost:8000 にアクセス
2. 同様の手順でPDFアップロードと翻訳が可能

## データの永続化

Docker Composeは以下のボリュームを作成して、データを永続化します:

- `./backend/uploads` - アップロードされたPDFファイル
- `./backend/storage` - ローカルデータベース (JSON形式)

これにより、コンテナを再起動してもデータが保持されます。

## コンテナ管理コマンド

### 起動・停止

```bash
# 起動 (バックグラウンド)
docker-compose up -d

# 停止
docker-compose down

# 停止 + ボリューム削除 (データも削除)
docker-compose down -v
```

### ログ確認

```bash
# 全サービスのログ
docker-compose logs -f

# バックエンドのみ
docker-compose logs -f backend

# フロントエンドのみ
docker-compose logs -f frontend
```

### コンテナ再ビルド

```bash
# コードを変更した場合、再ビルド
docker-compose up -d --build

# 特定のサービスのみ再ビルド
docker-compose up -d --build backend
```

### ステータス確認

```bash
# 実行中のコンテナ確認
docker-compose ps

# ヘルスチェック
curl http://localhost:8000/health
curl http://localhost:3000
```

## トラブルシューティング

### ポートが既に使用されている

**エラー**: `Bind for 0.0.0.0:3000 failed: port is already allocated`

**解決策**: `docker-compose.yml`のポート番号を変更

```yaml
services:
  frontend:
    ports:
      - "3001:3000"  # ローカルポートを3001に変更
```

### コンテナが起動しない

```bash
# ログを確認
docker-compose logs backend
docker-compose logs frontend

# コンテナ再起動
docker-compose restart

# 完全にクリーンアップして再起動
docker-compose down -v
docker-compose up -d --build
```

### Gemini API エラー

**エラー**: `401 Unauthorized` または `API key not valid`

**解決策**:
1. `.env`ファイルの`GEMINI_API_KEY`を確認
2. APIキーが正しいことを確認
3. コンテナを再起動: `docker-compose restart backend`

### ファイルアップロードエラー

**エラー**: ファイルサイズが大きすぎる

**解決策**: `.env`の`MAX_FILE_SIZE_MB`を増やす

```env
MAX_FILE_SIZE_MB=100
```

## 本番環境への移行

ローカルで動作確認後、本番環境にデプロイする場合:

### オプション1: Supabaseを使用

1. [Supabase](https://supabase.com/)でプロジェクト作成
2. `.env`に以下を追加:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_anon_key
   SUPABASE_SERVICE_KEY=your_service_role_key
   ```
3. データベーステーブルとStorageバケットを作成 (詳細は[production_deployment.md](./production_deployment.md)を参照)

### オプション2: クラウドサービスにデプロイ

詳細な手順は[production_deployment.md](./production_deployment.md)を参照:

- **Backend**: Cloud Run / Railway / Render
- **Frontend**: Vercel
- **Database**: Supabase

## リソース使用量

### 最小要件

- **CPU**: 2コア
- **メモリ**: 4GB
- **ディスク**: 10GB (PDFファイルを保存するため)

### 推奨環境

- **CPU**: 4コア
- **メモリ**: 8GB
- **ディスク**: 50GB

## セキュリティ

### APIキー管理

- `.env`ファイルは`.gitignore`に含まれており、Gitにコミットされません
- 本番環境では環境変数またはシークレット管理サービスを使用してください

### CORS設定

デフォルトでは`http://localhost:3000`のみ許可されています。本番環境では`docker-compose.yml`を編集:

```yaml
environment:
  - ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## サポート

問題が発生した場合:

1. [README.md](../README.md) - プロジェクト概要
2. [production_deployment.md](./production_deployment.md) - 本番環境デプロイ
3. [GitHub Issues](https://github.com/info-seifu/textbook-translation/issues) - 問題報告

---

**最終更新**: 2025-11-19
