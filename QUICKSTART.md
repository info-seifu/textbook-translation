# クイックスタート（ローカル環境）

最小限の設定で動作確認を行うためのガイドです。

## 前提条件

- Python 3.10以上がインストール済み
- **Gemini APIキー**と**Claude APIキー**を取得済み

## 5分でセットアップ

### 1. 依存関係のインストール

```bash
cd backend
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cd backend

# .envファイルを作成
cat > .env << 'EOL'
# 必須: APIキーを設定してください
GEMINI_API_KEY=あなたのGemini APIキー
CLAUDE_API_KEY=あなたのClaude APIキー

# 以下はデフォルトのままでOK
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=uploads
EOL

# .envファイルを編集してAPIキーを入力
nano .env  # または vi, vim, code など
```

**重要**: `GEMINI_API_KEY`と`CLAUDE_API_KEY`を実際の値に置き換えてください。

### 3. バックエンドの起動

```bash
# backend/ディレクトリから実行
python -m app.main
```

または

```bash
uvicorn app.main:app --reload
```

### 4. 動作確認

別のターミナルで実行：

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

✅ 両方のAPIが`true`になっていれば成功です！

### 5. PDFアップロードテスト（オプション）

サンプルPDFがある場合：

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/your/sample.pdf"
```

レスポンス例：
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "OCR processing started (writing direction will be auto-detected)"
}
```

## トラブルシューティング

### pdf2imageのエラー

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

### ポートが使用中

`.env`ファイルで別のポートに変更：

```bash
BACKEND_PORT=8001
```

起動：

```bash
uvicorn app.main:app --reload --port 8001
```

### APIキーエラー

- `.env`ファイルが`backend/`ディレクトリにあることを確認
- APIキーに余分なスペースがないか確認
- APIキーが有効か確認（コンソールで確認）

## フロントエンド（オプション）

バックエンドが動作したら、フロントエンドも起動できます：

```bash
cd ../frontend

# 依存関係インストール
npm install

# 環境変数設定
cat > .env.local << 'EOL'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
EOL

# 起動
npm run dev
```

ブラウザで `http://localhost:3000` にアクセス。

## 次のステップ

動作確認ができたら：

1. **サンプルPDFでテスト**
   - アップロード → OCR → 翻訳の一連の流れを確認

2. **Phase 2機能の実装**
   - Gemini翻訳エンジンの完全実装
   - 複数言語同時翻訳
   - エラーハンドリング強化

3. **本格的なセットアップ**
   - `SETUP_LOCAL.md`を参照して詳細な設定を確認

## データの保存場所

```
backend/
├── storage/
│   ├── database.json      # ジョブ情報
│   ├── pdfs/              # PDF
│   ├── documents/         # マークダウン
│   └── figures/           # 図解
└── uploads/               # 一時ファイル
```

データをクリアしたい場合は`storage/`ディレクトリを削除してください。
