# Pull Request: Windows .exe化対応（PyInstaller）

## 📋 概要

教科書翻訳システムをWindows .exeファイルとして配布できるようにしました。
PyInstallerを使用し、Pythonインストール不要で動作する実行ファイルを生成できます。

---

## 🎯 実装内容

### 1. launcher.py - アプリケーションランチャー

**機能:**
- FastAPIサーバーを自動起動
- 2秒後に自動的にブラウザを開く
- Ctrl+C で適切にシャットダウン
- エラーハンドリング
  - ポート競合の検出
  - 環境変数未設定の警告
  - わかりやすいエラーメッセージ

**コード例:**
```python
# ブラウザを自動起動（2秒後）
open_browser(url, delay=2.0)

# FastAPIサーバー起動
uvicorn.run(
    "app.main:app",
    host=host,
    port=port,
    log_level="info",
    access_log=True
)
```

### 2. textbook-translation.spec - PyInstaller設定

**特徴:**
- テンプレート・静的ファイルを自動同梱
- 必要なhiddenimportsを定義
  - uvicorn.logging
  - uvicorn.loops
  - weasyprint
  - cairocffi
- ワンディレクトリ形式（起動速度優先）
- コンソールウィンドウ表示（ログ確認用）

**データファイル:**
```python
datas = [
    ('app/templates', 'app/templates'),  # Jinja2テンプレート
    ('app/static', 'app/static'),        # CSS/JS/画像
]
```

### 3. build.bat - ビルドスクリプト

**5ステップのビルドプロセス:**
1. Python環境のチェック
2. 依存パッケージのインストール
3. PyInstallerでビルド実行
4. .envファイルの自動コピー
5. README.txtの自動生成

**出力:**
```
dist/textbook-translation/
  ├── textbook-translation.exe  # メイン実行ファイル
  ├── .env                       # 環境変数設定
  ├── README.txt                 # 使い方説明
  ├── app/                       # アプリケーションデータ
  │   ├── templates/
  │   └── static/
  └── (その他依存DLL・ライブラリ)
```

### 4. requirements.txt更新

**追加パッケージ:**
```
pyinstaller==6.3.0
```

---

## 🚀 使い方

### ビルド方法

```bash
cd backend
build.bat
```

### 実行方法

```bash
dist\textbook-translation\textbook-translation.exe
```

または、エクスプローラーで `textbook-translation.exe` をダブルクリック

### 配布方法

`dist\textbook-translation\` フォルダごとZIPで配布

---

## ✨ 主な機能

### 教師に優しい設計
- ✅ **Pythonインストール不要** - .exeファイルのみで動作
- ✅ **ダブルクリックで起動** - コマンドライン不要
- ✅ **自動ブラウザ起動** - URLを手入力不要
- ✅ **わかりやすいログ** - コンソールウィンドウにステータス表示
- ✅ **エラーメッセージ日本語** - トラブルシューティングが容易

### 技術的特徴
- ✅ **ワンディレクトリ形式** - 起動速度が速い
- ✅ **自動依存解決** - PyInstallerが必要なDLLを自動同梱
- ✅ **環境変数対応** - .envファイルでAPI キー設定
- ✅ **適切なシャットダウン** - Ctrl+C でクリーンに終了

---

## 📦 配布パッケージ構成

```
textbook-translation/
├── textbook-translation.exe    # メイン実行ファイル
├── .env                         # 環境変数設定（API キー）
├── README.txt                   # 使い方説明
├── app/
│   ├── templates/              # HTMLテンプレート
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── upload.html
│   │   └── status.html
│   └── static/                 # 静的ファイル
│       ├── css/
│       └── js/
├── _internal/                  # PyInstaller内部ファイル
│   ├── python39.dll
│   ├── (その他依存ライブラリ)
│   └── ...
└── (その他依存DLL)
```

**配布時の注意:**
- .envファイルには各自のAPI キーを設定してもらう
- README.txtに設定方法を記載

---

## 🔍 コード品質

- ✅ **Linter**: 0エラー、0警告
- ✅ **構文チェック**: 問題なし
- ✅ **コード整形**: PEP8準拠

---

## 📝 変更ファイル

### 新規作成
- `backend/launcher.py` - アプリケーションランチャー（92行）
- `backend/textbook-translation.spec` - PyInstaller設定（94行）
- `backend/build.bat` - ビルドスクリプト（105行）

### 変更
- `backend/requirements.txt` - pyinstaller==6.3.0 追加

---

## 🧪 テスト計画

### ビルドテスト
1. **依存パッケージインストール**
   - requirements.txtから正常にインストール
   - PyInstaller 6.3.0が利用可能

2. **ビルド実行**
   - `build.bat` が正常に完了
   - `dist/textbook-translation/` が生成される
   - 必要なファイルが全て同梱されている

3. **.exe実行**
   - ダブルクリックで起動
   - 2秒後にブラウザが開く
   - FastAPIサーバーが正常動作
   - WebUIがアクセス可能

4. **機能テスト**
   - PDFアップロード
   - OCR実行
   - 翻訳実行
   - ダウンロード（MD/HTML/PDF）

### エラーハンドリングテスト
- [ ] ポート8000が使用中の場合のエラーメッセージ
- [ ] .envファイルが無い場合の警告
- [ ] API キーが未設定の場合のエラー

---

## 🚀 次のステップ

このPRマージ後、以下の実装を進めます：

### Phase 3: Docker化
- `Dockerfile` 作成（WeasyPrint依存関係含む）
- `docker-compose.yml` 作成
- ローカルDocker環境でテスト

### Phase 4: クラウドデプロイ（オプション）
- Fly.io設定 (`fly.toml`)
- Oracle Cloud設定
- デプロイとテスト

---

## 📸 使用イメージ

**起動時:**
```
============================================================
📚 教科書翻訳システム
============================================================

🚀 サーバーを起動中...
   URL: http://localhost:8000

⚠️ 終了するには Ctrl+C を押してください
============================================================

🌐 ブラウザを起動中: http://localhost:8000
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

**終了時:**
```
^C
============================================================
👋 サーバーを終了しています...
============================================================
```

---

## 🎯 レビューポイント

- [ ] launcher.pyのエラーハンドリングは適切か
- [ ] .specファイルのhiddenimportsは十分か
- [ ] build.batのエラーチェックは適切か
- [ ] README.txtの説明はわかりやすいか
- [ ] 配布パッケージのサイズは許容範囲か

---

**ブランチ**: `claude/pyinstaller-build-01TLgqiVAKoPRgh2NQ1c4MCP`
**ベースブランチ**: `main`
**関連Issue**: N/A
**関連PR**: #3（ローカルWebUI実装）

---

## 📝 プルリクエスト作成方法

1. GitHubのリポジトリページにアクセス
2. "Pull requests" タブをクリック
3. "New pull request" ボタンをクリック
4. base: `main` ← compare: `claude/pyinstaller-build-01TLgqiVAKoPRgh2NQ1c4MCP` を選択
5. タイトル: **feat: Windows .exe化対応（PyInstaller）**
6. このファイルの内容をDescriptionにコピー＆ペースト
7. "Create pull request" をクリック
