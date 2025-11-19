# 教科書翻訳アプリ

Google Gemini APIを活用した、日本語教科書（縦書き・横書き）の多言語翻訳Webアプリケーション

## 📋 概要

本アプリケーションは、PDF形式の日本語教科書を自動でOCR処理し、複数の言語に翻訳するシステムです。

### 主な特徴

- **📖 縦書き・横書き自動判定**: Gemini Proが書字方向を自動認識
- **🎯 高精度OCR**: Gemini 2.5/3.0 Proによる高品質なテキスト抽出（切り替え可能）
- **🌍 多言語対応**: 英語、中国語、韓国語など複数言語に翻訳可能
- **🔄 翻訳エンジン選択**: Claude Sonnet（高品質）/ Gemini Flash（高速・低コスト）
- **📊 図解保持**: 図表や画像を含めたレイアウトを維持
- **💾 マスターファイル方式**: 1回のOCRで複数言語に展開可能
- **🚀 ローカル実行対応**: Supabase不要で即座に動作可能

## 🏗️ アーキテクチャ

```
PDF入力
  ↓
Gemini 2.5/3.0 Pro (OCR + 図解抽出 + 書字方向自動判定)
  ↓
日本語マークダウン (マスター) → storage/documents/{job_id}/master_ja.md
  ↓
翻訳エンジン (Gemini Flash / Claude Sonnet)
  ↓
多言語マークダウン (en/zh/ko/etc.) → storage/documents/{job_id}/translated_{lang}.md
```

## 🛠️ 技術スタック

### バックエンド
- Python 3.10+
- FastAPI (API + WebUI)
- Google Gemini API
  - Gemini 2.5 Pro (OCR、無料枠あり)
  - Gemini 3.0 Pro (OCR、課金必要、高精度)
  - Gemini 2.5 Flash (翻訳、高速・低コスト)
- Anthropic Claude API (Sonnet 4.5)
- ローカルDB/ストレージ (JSONベース、Supabase不要)

### フロントエンド
- Next.js 14+ (App Router) - オプショナル
- TypeScript
- Tailwind CSS
- FastAPI内蔵WebUI - 実装済み

## 📁 プロジェクト構造

```
textbook-translation/
├── backend/              # FastAPI バックエンド（実装完了）
│   ├── app/
│   │   ├── api/         # APIエンドポイント（実装済み）
│   │   ├── services/    # OCR・翻訳サービス（実装済み）
│   │   ├── models/      # データモデル（実装済み）
│   │   ├── utils/       # ローカルDB/ストレージ等（実装済み）
│   │   ├── static/      # WebUI用静的ファイル（実装済み）
│   │   └── templates/   # WebUI用HTMLテンプレート（実装済み）
│   ├── tests/           # テストコード（実装済み）
│   ├── launcher.py      # スタンドアロン起動（実装済み）
│   └── requirements.txt
│
├── storage/             # ローカルストレージ（自動生成）
│   ├── database.json    # JSONベースDB
│   ├── pdfs/           # アップロードPDF
│   ├── documents/      # マークダウンファイル
│   └── figures/        # 抽出図解
│
├── frontend/           # Next.js フロントエンド（部分実装）
│   ├── app/
│   ├── components/
│   └── lib/
│
├── docs/               # ドキュメント
│   └── textbook-translation-app-design.md
│
└── samples/            # サンプルPDF
    └── pdf/
        ├── horizontal/ # 横書きサンプル
        └── vertical/   # 縦書きサンプル×2
```

## 🚀 セットアップ

### 必須環境

- Python 3.10以上
- Google Gemini APIキー
- Anthropic Claude APIキー

### オプショナル

- Node.js 18以上（Next.jsフロントエンド使用時）
- Supabaseアカウント（本番環境使用時）

### 環境変数設定

#### 最小構成（ローカル実行）

`.env`ファイルを `backend/` ディレクトリ内に作成:

```bash
# 必須: APIキーのみ
GEMINI_API_KEY=your_gemini_api_key
CLAUDE_API_KEY=your_claude_api_key

# オプショナル: Gemini 3.0使用時（課金必要）
USE_GEMINI_3=false
```

#### 本番環境構成（Supabase使用時）

```bash
# 必須
GEMINI_API_KEY=your_gemini_api_key
CLAUDE_API_KEY=your_claude_api_key

# Supabase設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### クイックスタート

#### 方法1: スタンドアロン起動（推奨）

```bash
cd backend
pip install -r requirements.txt

# .envファイルを設定
cp .env.example .env
# エディタでGEMINI_API_KEYとCLAUDE_API_KEYを設定

# 起動
python launcher.py
```

ブラウザで http://localhost:8000 にアクセス

#### 方法2: uvicorn起動

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 方法3: Next.jsフロントエンド使用（オプショナル）

```bash
# バックエンド起動
cd backend
python launcher.py

# 別ターミナルでフロントエンド起動
cd frontend
npm install
npm run dev
```

Next.jsフロントエンド: http://localhost:3000

## 📖 使い方

1. **PDFアップロード**: 翻訳したい教科書PDFをアップロード
2. **OCR処理**: Gemini 2.5 Proが自動で書字方向を判定してテキスト抽出
3. **翻訳**: 希望する言語と翻訳エンジンを選択
4. **ダウンロード**: Markdown/HTML/PDF形式でダウンロード

## 💰 コスト試算（50ページの場合）

| 構成 | コスト | 用途 |
|------|--------|------|
| OCR (Gemini 2.5 Pro) + 翻訳 (Claude Sonnet) | $0.36 | 品質最重視 |
| OCR (Gemini 2.5 Pro) + 翻訳 (Gemini Flash) | $0.18 | コスト重視 |
| OCR (Gemini 3.0 Pro) + 翻訳 (Claude Sonnet) | $0.50 | 最高精度（課金必要） |

### Gemini バージョン比較

| モデル | 無料枠 | 精度 | 用途 |
|--------|--------|------|------|
| Gemini 2.5 Pro | ⭕ あり | 高 | 開発・テスト推奨 |
| Gemini 3.0 Pro | ❌ なし | 最高 | 本番環境・高精度要求時 |

## 📚 ドキュメント

詳細な設計書は [docs/textbook-translation-app-design.md](docs/textbook-translation-app-design.md) を参照してください。

## 🗺️ 実装状況

### ✅ Phase 1: 基本機能（完了）
- [x] 設計書作成
- [x] ローカルDB/ストレージ実装
- [x] バックエンド基盤構築（FastAPI + WebUI）
- [x] Gemini OCR実装（2.5/3.0切り替え対応）
- [x] Claude翻訳実装
- [x] フロントエンド基本UI（Next.js）

### ✅ Phase 2: エンジン選択＆多言語対応（完了）
- [x] Gemini翻訳実装
- [x] エンジン切り替え機能（`USE_GEMINI_3`環境変数）
- [x] 複数言語サポート
- [x] バッチ翻訳機能

### ✅ Phase 3: 品質向上＆最適化（完了）
- [x] エラーハンドリング強化
- [x] リトライ機能（exponential backoff）
- [x] HTML/PDF生成機能
- [x] テストコード整備

### 🔄 Phase 4: 追加機能（進行中）
- [ ] Next.jsフロントエンド完成
- [ ] 本番環境デプロイ（Vercel + Supabase）
- [ ] ドキュメント整備

## 🤝 コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📄 ライセンス

[MIT](LICENSE)

## 👥 作成者

開発: Claude Code による支援

---

**Note**: このプロジェクトは開発中です。本番環境での使用前に十分なテストを行ってください。
