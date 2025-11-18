# Docker デプロイガイド

教科書翻訳システムをDockerコンテナとしてビルド・実行・デプロイする方法を説明します。

---

## 📋 目次

1. [前提条件](#前提条件)
2. [ローカル開発](#ローカル開発)
3. [Fly.io デプロイ](#flyio-デプロイ)
4. [Oracle Cloud デプロイ](#oracle-cloud-デプロイ)
5. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 必要なソフトウェア

- **Docker** (20.10以上)
- **Docker Compose** (v2.0以上)

インストール確認:
```bash
docker --version
docker compose version
```

### 環境変数の設定

`backend/.env` ファイルを作成し、以下を設定:

```env
# API キー（必須）
GEMINI_API_KEY=your_gemini_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here

# バックエンド設定
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# ストレージ設定
STORAGE_TYPE=local  # local または supabase

# CORS設定（必要に応じて）
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Supabase設定（使用する場合）
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key
```

---

## ローカル開発

### 1. Docker Composeで起動

最も簡単な方法:

```bash
cd backend
docker compose up
```

バックグラウンドで起動:
```bash
docker compose up -d
```

### 2. ログ確認

```bash
docker compose logs -f
```

### 3. アクセス

ブラウザで開く:
```
http://localhost:8000
```

### 4. 停止

```bash
docker compose down
```

データを保持したまま停止:
```bash
docker compose stop
```

### 5. 再ビルド

コードを変更した場合:
```bash
docker compose up --build
```

---

## Fly.io デプロイ

### 前提条件

- Fly.ioアカウント作成
- `flyctl` CLI インストール

```bash
# macOS/Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
```

### 1. ログイン

```bash
flyctl auth login
```

### 2. アプリケーション作成

```bash
cd backend
flyctl launch
```

対話形式で以下を選択:
- **App name**: textbook-translation (または任意の名前)
- **Region**: Tokyo (nrt)
- **PostgreSQL**: No（ローカルストレージ使用）
- **Redis**: No

### 3. fly.toml 設定

`backend/fly.toml` を確認・編集:

```toml
app = "textbook-translation"
primary_region = "nrt"  # Tokyo

[build]
  dockerfile = "Dockerfile"

[env]
  BACKEND_HOST = "0.0.0.0"
  BACKEND_PORT = "8000"
  STORAGE_TYPE = "local"

[[services]]
  internal_port = 8000
  protocol = "tcp"
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

  [[services.tcp_checks]]
    interval = "15s"
    timeout = "2s"
    grace_period = "5s"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

### 4. シークレット設定

```bash
flyctl secrets set GEMINI_API_KEY=your_key_here
flyctl secrets set CLAUDE_API_KEY=your_key_here
```

### 5. デプロイ

```bash
flyctl deploy
```

### 6. アプリケーションにアクセス

```bash
flyctl open
```

または、URL直接アクセス:
```
https://textbook-translation.fly.dev
```

### 7. ログ確認

```bash
flyctl logs
```

### 8. スケーリング

```bash
# マシン数を調整
flyctl scale count 2

# マシンサイズを調整
flyctl scale vm shared-cpu-1x --memory 512
```

### 9. 費用

- **共有CPU 1x (256MB RAM)**: 約$3/月
- **スリープ機能**: アクセスがない時は自動停止（無料）

---

## Oracle Cloud デプロイ

### 前提条件

- Oracle Cloud アカウント（Always Free Tier）
- SSH キーペア

### 1. VMインスタンス作成

1. Oracle Cloud Console にログイン
2. **Compute** → **Instances** → **Create Instance**
3. 以下を選択:
   - **Image**: Ubuntu 22.04
   - **Shape**: VM.Standard.E2.1.Micro (Always Free)
   - **Network**: デフォルトVCN
   - **SSH Keys**: 公開鍵をアップロード

### 2. ファイアウォール設定

セキュリティリストで以下を許可:

```
Ingress Rule:
- Source: 0.0.0.0/0
- Protocol: TCP
- Port: 80, 443, 8000
```

### 3. VMに接続

```bash
ssh -i ~/.ssh/your_key ubuntu@<VM_PUBLIC_IP>
```

### 4. Docker インストール

```bash
# Dockerインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose インストール
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 再ログイン
exit
ssh -i ~/.ssh/your_key ubuntu@<VM_PUBLIC_IP>
```

### 5. リポジトリクローン

```bash
git clone https://github.com/info-seifu/textbook-translation.git
cd textbook-translation/backend
```

### 6. 環境変数設定

```bash
nano .env
```

API キーを設定して保存 (Ctrl+X → Y → Enter)

### 7. アプリケーション起動

```bash
docker compose up -d
```

### 8. Nginx リバースプロキシ設定（オプション）

HTTPSを有効にする場合:

```bash
sudo apt-get install nginx certbot python3-certbot-nginx

# Nginx設定
sudo nano /etc/nginx/sites-available/textbook-translation
```

設定内容:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

有効化:
```bash
sudo ln -s /etc/nginx/sites-available/textbook-translation /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL証明書取得（Let's Encrypt）
sudo certbot --nginx -d your-domain.com
```

### 9. 自動起動設定

```bash
# Docker Compose自動起動
sudo systemctl enable docker
```

---

## トラブルシューティング

### コンテナが起動しない

**ログ確認:**
```bash
docker compose logs
```

**よくある原因:**
- `.env` ファイルが無い → 作成してAPI キーを設定
- ポート8000が使用中 → `docker compose down` で停止
- メモリ不足 → `docker compose.yml` のリソース制限を調整

### WeasyPrintエラー

**エラー例:**
```
OSError: cannot load library 'gobject-2.0-0'
```

**解決策:**
Dockerfileに依存関係が含まれているか確認。再ビルド:
```bash
docker compose up --build
```

### ファイルアップロードエラー

**原因:**
- アップロードディレクトリの権限不足

**解決策:**
```bash
# ホスト側でディレクトリ作成
mkdir -p uploads storage
chmod 777 uploads storage

# 再起動
docker compose restart
```

### Fly.io デプロイエラー

**シークレット未設定:**
```bash
flyctl secrets list
```

API キーが設定されていない場合:
```bash
flyctl secrets set GEMINI_API_KEY=xxx CLAUDE_API_KEY=yyy
```

**リージョン変更:**
```bash
flyctl regions list
flyctl regions set nrt  # Tokyo
```

### Oracle Cloud 接続できない

**ファイアウォール確認:**
1. セキュリティリスト設定を確認
2. VM内のufwを確認:
```bash
sudo ufw status
sudo ufw allow 8000/tcp
```

**Nginxエラー:**
```bash
sudo nginx -t
sudo systemctl status nginx
sudo journalctl -u nginx -f
```

---

## パフォーマンスチューニング

### Dockerイメージサイズ削減

マルチステージビルドを使用（Dockerfile修正例）:
```dockerfile
# ビルドステージ
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# 実行ステージ
FROM python:3.11-slim
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
...
```

### メモリ使用量削減

`docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # 256Mに削減（最小構成）
```

---

## セキュリティベストプラクティス

1. **環境変数を`.env`で管理** - リポジトリにコミットしない
2. **非rootユーザーで実行** - Dockerfileに含まれている
3. **イメージの定期更新** - `docker compose pull && docker compose up -d`
4. **HTTPSを使用** - Fly.ioは自動、Oracle CloudはLet's Encrypt
5. **ファイアウォール設定** - 必要なポートのみ開放

---

## まとめ

### ローカル開発
```bash
cd backend
docker compose up
```
→ http://localhost:8000

### Fly.io デプロイ
```bash
flyctl launch
flyctl secrets set GEMINI_API_KEY=xxx CLAUDE_API_KEY=yyy
flyctl deploy
```
→ https://your-app.fly.dev

### Oracle Cloud デプロイ
```bash
# VM上で
git clone ...
cd backend
docker compose up -d
```
→ http://your-vm-ip:8000

---

**サポート:**
https://github.com/info-seifu/textbook-translation/issues
