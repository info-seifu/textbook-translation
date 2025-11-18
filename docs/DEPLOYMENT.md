# デプロイ・運用設計書

## 📋 概要

教科書翻訳システムのデプロイ・運用戦略を定義します。
ローカル環境（Windows .exe配布）とクラウドデプロイの両方に対応した柔軟な設計です。

---

## 🎯 運用シナリオ

### シナリオ1: ローカル環境（Windows .exe配布）

**対象ユーザー：**
- Pythonを使ったことがない教員
- 機密性を重視する組織
- 個人利用

**特徴：**
- ✅ ダブルクリックで起動
- ✅ コマンド入力不要
- ✅ ブラウザ自動オープン
- ✅ APIキー以外の設定不要
- ✅ インターネット接続のみ必要（Gemini/Claude API呼び出し用）

**配布形態：**
```
教科書翻訳_v1.0.zip
├── 教科書翻訳.exe          # PyInstallerでパッケージ化
├── README.txt             # 使い方
├── 初回設定ガイド.txt      # APIキー設定方法
└── サンプル教科書.pdf      # テスト用
```

---

### シナリオ2: クラウドデプロイ（Fly.io - 推奨）

**対象ユーザー：**
- 複数の教員が共同利用
- 外出先からもアクセスしたい
- チームでの利用

**特徴：**
- ✅ どこからでもアクセス可能
- ✅ 自動スケーリング
- ✅ HTTPS対応
- ✅ GitHubプッシュで自動デプロイ

**月額コスト：**
- 基本プラン: **$3/月（約450円）**
- ストレージ 3GB: 無料
- **合計: $3/月**

---

### シナリオ3: クラウドデプロイ（Oracle Cloud - 完全無料）

**対象ユーザー：**
- コストを完全にゼロにしたい
- 技術的な設定が可能

**特徴：**
- ✅ 永久無料
- ✅ ARM CPU 4コア + 24GB RAM
- ✅ ストレージ 200GB
- ✅ 転送量 10TB/月

**デメリット：**
- セットアップがやや複雑
- ARMアーキテクチャ（Dockerイメージ要調整）

---

## 🏗️ アーキテクチャ

### 統一アーキテクチャ（全シナリオ共通）

```
┌─────────────────────────────────────┐
│  WebUI（ブラウザ）                  │
│  - PDFアップロード                   │
│  - 翻訳進捗表示                      │
│  - ダウンロード                      │
└──────────┬──────────────────────────┘
           │ HTTP/REST API
┌──────────▼──────────────────────────┐
│  FastAPI バックエンド               │
│  - Jinja2テンプレート（WebUI）      │
│  - REST API                         │
│  - OCR/翻訳オーケストレーション      │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐  ┌─────────────┐
│ ローカル │  │ Gemini API  │
│ストレージ│  │ Claude API  │
│ (JSON DB)│  └─────────────┘
└─────────┘
```

**ポイント：**
- ストレージ抽象化層により、ローカル/クラウドの切り替えが容易
- 同じコードベースで全シナリオに対応

---

## 📦 技術スタック

### バックエンド
- **Python 3.11+**
- **FastAPI** - Web API + テンプレート
- **Jinja2** - HTMLテンプレートエンジン
- **Uvicorn** - ASGIサーバー

### WebUI
- **Jinja2テンプレート** - サーバーサイドレンダリング
- **TailwindCSS** - スタイリング（CDN）
- **Vanilla JavaScript** - インタラクティブ機能

### パッケージング
- **PyInstaller** - Windows .exe化
- **Docker** - コンテナ化

### デプロイ
- **Fly.io** - 推奨クラウドプラットフォーム
- **Oracle Cloud** - 無料代替案

---

## 📁 ディレクトリ構成

```
textbook-translation/
├── backend/
│   ├── app/
│   │   ├── templates/              # WebUI テンプレート
│   │   │   ├── base.html          # 基本レイアウト
│   │   │   ├── index.html         # トップページ
│   │   │   ├── upload.html        # アップロード画面
│   │   │   ├── status.html        # ステータス表示
│   │   │   └── result.html        # 結果表示
│   │   │
│   │   ├── static/                 # 静的ファイル
│   │   │   ├── css/
│   │   │   │   └── style.css      # カスタムスタイル
│   │   │   ├── js/
│   │   │   │   └── app.js         # フロントエンドロジック
│   │   │   └── images/
│   │   │       └── logo.png
│   │   │
│   │   ├── api/                    # REST API（既存）
│   │   │   ├── upload.py
│   │   │   ├── translate.py
│   │   │   ├── status.py
│   │   │   ├── download.py
│   │   │   └── batch_translate.py
│   │   │
│   │   ├── services/               # ビジネスロジック
│   │   │   ├── gemini_ocr_service.py
│   │   │   ├── claude_translator.py
│   │   │   ├── gemini_translator.py
│   │   │   ├── html_generator.py
│   │   │   ├── pdf_generator.py
│   │   │   └── ...
│   │   │
│   │   ├── utils/
│   │   │   ├── local_db.py
│   │   │   ├── local_storage.py
│   │   │   └── ...
│   │   │
│   │   └── main.py                 # エントリーポイント
│   │
│   ├── launcher.py                 # .exe起動スクリプト
│   ├── Dockerfile                  # Docker設定
│   ├── requirements.txt
│   └── .env.example
│
├── docker-compose.yml              # ローカルDocker開発環境
├── fly.toml                        # Fly.io設定
├── .dockerignore
├── docs/
│   ├── DEPLOYMENT.md               # この文書
│   ├── LOCAL_SETUP.md              # ローカルセットアップ
│   └── CLOUD_DEPLOY.md             # クラウドデプロイ手順
│
└── README.md
```

---

## 🚀 実装手順

### Phase 1: WebUI実装（ローカル対応）

**実装内容：**
1. テンプレートディレクトリ作成
2. HTMLテンプレート作成
   - トップページ
   - アップロード画面
   - ステータス表示
   - 結果・ダウンロード画面
3. 静的ファイル（CSS/JS）
4. main.py にWebUIルート追加

**完了条件：**
- ローカルで `uvicorn app.main:app` で起動し、ブラウザでアクセス可能
- PDFアップロード → 翻訳 → ダウンロードの一連の流れが完動

### Phase 2: Windows .exe 化

**実装内容：**
1. launcher.py 作成（起動スクリプト）
2. PyInstaller設定
3. .exe ビルドとテスト
4. 配布パッケージ作成

**完了条件：**
- `教科書翻訳.exe` をダブルクリックで起動
- ブラウザが自動オープン
- 全機能が動作

### Phase 3: Docker化

**実装内容：**
1. Dockerfile作成
2. docker-compose.yml作成
3. .dockerignore設定
4. ローカルDocker環境でテスト

**完了条件：**
- `docker-compose up` で起動
- すべての機能が動作

### Phase 4: Fly.io デプロイ

**実装内容：**
1. fly.toml作成
2. 環境変数設定
3. デプロイとテスト

**完了条件：**
- `flyctl deploy` でデプロイ成功
- HTTPS でアクセス可能
- 本番環境で全機能動作

---

## 🔧 設定ファイル

### Dockerfile（クラウドデプロイ用）

```dockerfile
FROM python:3.11-slim

# WeasyPrint用のシステム依存関係
RUN apt-get update && apt-get install -y \
    gcc \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### fly.toml（Fly.io設定）

```toml
app = "textbook-translation"
primary_region = "nrt"  # 東京リージョン

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 1024
```

### docker-compose.yml（ローカル開発用）

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
    volumes:
      - ./storage:/app/storage
    restart: unless-stopped
```

---

## 💰 コスト試算

### シナリオ別コスト

| シナリオ | 初期費用 | 月額費用 | 年間費用 | 備考 |
|---------|---------|---------|---------|------|
| **ローカル.exe** | ¥0 | ¥0 | ¥0 | API費用のみ |
| **Fly.io** | ¥0 | ¥450 | ¥5,400 | 東京リージョン |
| **Oracle Cloud** | ¥0 | ¥0 | ¥0 | 永久無料枠 |

### API費用（参考）

**50ページ教科書 × 1言語翻訳の場合：**
- OCR（Gemini 2.0 Flash）: $0.175
- 翻訳（Claude Sonnet）: $0.18
- **合計: $0.355（約50円）**

**月間100冊処理の場合：**
- API費用: $35.5（約5,000円）

**推奨：**
- **少量利用（月10冊未満）**: ローカル.exe
- **中量利用（月10-50冊）**: Fly.io
- **大量利用（月50冊以上）**: Oracle Cloud（無料）

---

## 🔐 セキュリティ考慮事項

### ローカル環境
- APIキーは `.env` ファイルで管理
- PDFファイルはローカルストレージに保存
- 外部への通信は Gemini/Claude API のみ

### クラウド環境
- HTTPS強制（Fly.io自動対応）
- 環境変数で APIキー管理（平文保存なし）
- Basic認証の追加推奨（共同利用時）

### 推奨セキュリティ対策
```python
# app/main.py に追加（オプション）
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "your_password")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
```

---

## 📊 パフォーマンス

### 処理時間目安

| 処理 | 時間 | 備考 |
|-----|------|------|
| PDFアップロード | 1-5秒 | ファイルサイズ依存 |
| OCR（10ページ） | 1-2分 | Gemini API速度依存 |
| 翻訳（10ページ） | 30-60秒 | Claude/Gemini速度依存 |
| HTML生成 | 1-2秒 | ほぼ即時 |
| PDF生成 | 3-5秒 | WeasyPrint処理時間 |

### スケーラビリティ

**ローカル環境：**
- 同時処理数: 1（単一ユーザー）
- 制限: なし

**Fly.io（1GB RAM）：**
- 同時処理数: 2-3リクエスト
- メモリ不足時は自動スケール

---

## 🔄 アップデート戦略

### ローカル.exe
1. 新バージョンの .exe をビルド
2. ZIPファイルで配布
3. ユーザーが手動で上書き

### クラウド（Fly.io）
1. GitHubにプッシュ
2. `flyctl deploy` で自動デプロイ
3. ゼロダウンタイム更新

---

## 📝 ドキュメント

### ユーザー向け
- `README.txt` - 基本的な使い方
- `初回設定ガイド.txt` - APIキー設定
- `トラブルシューティング.txt` - よくある問題

### 開発者向け
- `docs/LOCAL_SETUP.md` - ローカル開発環境構築
- `docs/CLOUD_DEPLOY.md` - クラウドデプロイ手順
- `docs/API_REFERENCE.md` - API仕様

---

## 🎯 まとめ

### 推奨デプロイ戦略

**Phase 1（現在）: ローカル.exe配布**
- 対象: 個人・小規模利用
- コスト: ¥0/月
- 実装難易度: 中

**Phase 2（拡張時）: Fly.io デプロイ**
- 対象: チーム利用（5-10人）
- コスト: ¥450/月
- 実装難易度: 低

**Phase 3（大規模時）: Oracle Cloud**
- 対象: 組織全体（20人以上）
- コスト: ¥0/月
- 実装難易度: 高

### 次のステップ

1. ✅ WebUI実装
2. ✅ ローカルテスト
3. Windows .exe 化
4. クラウドデプロイ（必要に応じて）

---

**作成日**: 2025年1月14日
**バージョン**: 1.0
**対象**: 教科書翻訳システム
**ステータス**: 設計完了、実装開始
