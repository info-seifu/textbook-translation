# CI/CD パイプライン

このプロジェクトでは、GitHub Actionsを使用して自動テスト、リント、ビルド、デプロイを実行しています。

## ワークフロー一覧

### 1. Tests (`test.yml`)

**トリガー:**
- `main`ブランチへのプッシュ
- `main`ブランチへのプルリクエスト
- `backend/**`配下のファイル変更時

**実行内容:**
- Python 3.11でテスト実行
- pytest + coverage実行
- カバレッジレポート生成
- Codecovへのアップロード（オプション）

**必要なシークレット:**
- `GEMINI_API_KEY` (オプション - テスト用)
- `CLAUDE_API_KEY` (オプション - テスト用)
- `CODECOV_TOKEN` (オプション - Codecov連携用)

**成果物:**
- HTMLカバレッジレポート（30日間保存）

---

### 2. Lint (`lint.yml`)

**トリガー:**
- `main`ブランチへのプッシュ
- `main`ブランチへのプルリクエスト
- `backend/**/*.py`ファイル変更時

**実行内容:**
- flake8による構文チェック
- コーディング規約チェック
- 重大なエラーの検出

**チェック内容:**
- 構文エラー (E9)
- 未定義の名前 (F63, F7, F82)
- 行の長さ: 最大100文字
- PEP8準拠

**成果物:**
- flake8 HTMLレポート（30日間保存）

---

### 3. Build Windows Executable (`build.yml`)

**トリガー:**
- `main`ブランチへのプッシュ
- タグ作成時 (`v*`)
- `backend/**`配下のファイル変更時
- 手動トリガー（workflow_dispatch）

**実行内容:**
- Windows環境でPyInstallerビルド
- `.env.example`のコピー
- README生成
- ZIPアーカイブ作成

**成果物:**
- `textbook-translation-windows.zip`（90日間保存）
- タグ作成時はGitHub Releaseに自動アップロード

**ビルド内容:**
```
textbook-translation-windows.zip
├── textbook-translation.exe
├── .env.example
├── README.txt
└── (その他依存ファイル)
```

---

### 4. Build and Push Docker Image (`docker.yml`)

**トリガー:**
- `main`ブランチへのプッシュ
- タグ作成時 (`v*`)
- `backend/**`配下のファイル変更時
- 手動トリガー（workflow_dispatch）

**実行内容:**
- マルチアーキテクチャビルド（amd64, arm64）
- GitHub Container Registry (ghcr.io) へのプッシュ
- イメージの起動テスト

**イメージタグ:**
- `main` - mainブランチの最新版
- `v1.2.3` - セマンティックバージョン
- `v1.2` - メジャー.マイナーバージョン
- `v1` - メジャーバージョン
- `sha-<commit>` - コミットSHA

**プル方法:**
```bash
docker pull ghcr.io/info-seifu/textbook-translation:main
```

---

## セットアップ手順

### 1. GitHub Secretsの設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定：

**必須:**
- なし（すべてオプション）

**オプション:**
- `GEMINI_API_KEY` - Gemini APIキー（実際のAPI呼び出しテスト用）
- `CLAUDE_API_KEY` - Claude APIキー（実際のAPI呼び出しテスト用）
- `CODECOV_TOKEN` - Codecov連携トークン

### 2. GitHub Container Registryの設定

Dockerイメージのプッシュには追加設定不要（GitHub Actionsのデフォルト権限で動作）

### 3. Codecov連携（オプション）

1. https://codecov.io/ でアカウント作成
2. リポジトリを連携
3. トークンを取得
4. GitHub Secretsに`CODECOV_TOKEN`を追加

---

## ワークフローの確認方法

### GitHub UI
1. リポジトリページの「Actions」タブをクリック
2. 各ワークフローの実行履歴を確認
3. ログ、成果物のダウンロードが可能

### バッジの追加

README.mdに以下のバッジを追加できます：

```markdown
![Tests](https://github.com/info-seifu/textbook-translation/actions/workflows/test.yml/badge.svg)
![Lint](https://github.com/info-seifu/textbook-translation/actions/workflows/lint.yml/badge.svg)
![Build](https://github.com/info-seifu/textbook-translation/actions/workflows/build.yml/badge.svg)
![Docker](https://github.com/info-seifu/textbook-translation/actions/workflows/docker.yml/badge.svg)
```

---

## ローカルでの実行

CI/CDと同じチェックをローカルで実行する方法：

### テスト
```bash
cd backend
pytest -v --cov=app --cov-report=html
```

### リント
```bash
cd backend
flake8 app tests --max-line-length=100
```

### ビルド（Windows）
```bash
cd backend
pyinstaller textbook-translation.spec
```

### ビルド（Docker）
```bash
cd backend
docker build -t textbook-translation:local .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e CLAUDE_API_KEY=your_key \
  textbook-translation:local
```

---

## トラブルシューティング

### テストが失敗する

1. **依存関係のエラー**
   - `requirements.txt`が最新か確認
   - システム依存関係（Cairo, Pangoなど）が不足している可能性

2. **APIキーエラー**
   - テストはモックを使用するため、実際のAPIキーは不要
   - モックが正しく設定されているか確認

### ビルドが失敗する

1. **PyInstallerエラー**
   - `textbook-translation.spec`の設定を確認
   - 隠しインポートが正しく設定されているか確認

2. **Dockerビルドエラー**
   - `Dockerfile`の構文を確認
   - ベースイメージがプルできるか確認

### プッシュ権限エラー

1. **GitHub Container Registry**
   - リポジトリの Settings → Actions → General
   - "Workflow permissions"を"Read and write permissions"に設定

---

## ベストプラクティス

### プルリクエスト
- すべてのテストが成功してからマージ
- リントエラーは必ず修正
- カバレッジレポートを確認

### リリース
1. 機能開発が完了したらmainにマージ
2. セマンティックバージョニングに従ってタグを作成
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. 自動的にビルド・デプロイが実行される
4. GitHub Releasesで配布

### 手動トリガー
緊急時やテスト時は手動でワークフローを実行可能：
1. Actions → 該当ワークフロー → "Run workflow"

---

## パフォーマンス最適化

### キャッシュ
- Pythonパッケージ: `setup-python`のcacheオプション使用
- Dockerレイヤー: GitHub Actions Cache使用

### 並列実行
- 複数Pythonバージョンでのテスト（必要に応じて）
- マルチアーキテクチャビルド（amd64, arm64）

### コスト削減
- プルリクエストではDockerプッシュをスキップ
- 成果物の保持期間を適切に設定（30-90日）

---

## セキュリティ

### シークレット管理
- APIキーは必ずGitHub Secretsで管理
- `.env`ファイルはコミットしない
- `.env.example`のみをコミット

### 依存関係
- Dependabotで自動更新
- 定期的なセキュリティスキャン

### イメージのセキュリティ
- 非rootユーザーで実行
- 最小限の依存関係のみインストール
- 定期的なベースイメージ更新
