# 教科書翻訳アプリ

Google Gemini APIを活用した、日本語教科書（縦書き・横書き）の多言語翻訳Webアプリケーション

## 📋 概要

本アプリケーションは、PDF形式の日本語教科書を自動でOCR処理し、複数の言語に翻訳するシステムです。

### 主な特徴

- **📖 縦書き・横書き自動判定**: Gemini 2.5 Proが書字方向を自動認識
- **🎯 高精度OCR**: Gemini 2.5 Proによる高品質なテキスト抽出
- **🌍 多言語対応**: 英語、中国語、韓国語など複数言語に翻訳可能
- **🔄 翻訳エンジン選択**: Claude Sonnet（高品質）/ Gemini Flash（高速・低コスト）
- **📊 図解保持**: 図表や画像を含めたレイアウトを維持
- **💾 マスターファイル方式**: 1回のOCRで複数言語に展開可能

## 🏗️ アーキテクチャ

```
PDF入力
  ↓
Gemini 2.5 Pro (OCR + 図解抽出)
  ↓
日本語マークダウン (マスター)
  ↓
翻訳エンジン (Gemini Flash / Claude Sonnet)
  ↓
多言語マークダウン (en/zh/ko/etc.)
```

## 🛠️ 技術スタック

### バックエンド
- Python 3.10+
- FastAPI
- Google Gemini API (2.5 Pro / 2.5 Flash)
- Anthropic Claude API (Sonnet 4.5)
- Supabase (データベース・ストレージ)

### フロントエンド
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui

## 📁 プロジェクト構造

```
textbook-translation/
├── backend/           # FastAPI バックエンド
│   ├── app/
│   │   ├── api/      # APIエンドポイント
│   │   ├── services/ # OCR・翻訳サービス
│   │   └── models/   # データモデル
│   └── requirements.txt
│
├── frontend/         # Next.js フロントエンド
│   ├── app/
│   ├── components/
│   └── lib/
│
├── docs/             # ドキュメント
│   └── textbook-translation-app-design.md
│
└── samples/          # サンプルPDF
    └── pdf/
        ├── horizontal/
        └── vertical/
```

## 🚀 セットアップ

### 前提条件

- Python 3.10以上
- Node.js 18以上
- Supabaseアカウント
- Google Gemini APIキー
- Anthropic Claude APIキー

### 環境変数

`.env`ファイルを作成し、以下を設定:

```bash
# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Anthropic Claude
CLAUDE_API_KEY=your_claude_api_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### バックエンドのセットアップ

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### フロントエンドのセットアップ

```bash
cd frontend
npm install
npm run dev
```

## 📖 使い方

1. **PDFアップロード**: 翻訳したい教科書PDFをアップロード
2. **OCR処理**: Gemini 2.5 Proが自動で書字方向を判定してテキスト抽出
3. **翻訳**: 希望する言語と翻訳エンジンを選択
4. **ダウンロード**: Markdown/HTML/PDF形式でダウンロード

## 💰 コスト試算（50ページの場合）

| 構成 | コスト |
|------|--------|
| OCR (Gemini 2.5 Pro) + 翻訳 (Claude Sonnet) | $0.36 |
| OCR (Gemini 2.5 Pro) + 翻訳 (Gemini 2.5 Flash) | $0.18 |

## 📚 ドキュメント

詳細な設計書は [docs/textbook-translation-app-design.md](docs/textbook-translation-app-design.md) を参照してください。

## 🗺️ ロードマップ

### Phase 1: 基本機能（現在）
- [x] 設計書作成
- [ ] Supabaseセットアップ
- [ ] バックエンド基盤構築
- [ ] Gemini OCR実装
- [ ] Claude翻訳実装
- [ ] フロントエンド基本UI

### Phase 2: エンジン選択＆多言語対応
- [ ] Gemini翻訳実装
- [ ] エンジン切り替え機能
- [ ] 複数言語サポート

### Phase 3: 品質向上＆最適化
- [ ] エラーハンドリング強化
- [ ] パフォーマンス最適化
- [ ] デプロイ準備

## 🤝 コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📄 ライセンス

[MIT](LICENSE)

## 👥 作成者

開発: Claude Code による支援

---

**Note**: このプロジェクトは開発中です。本番環境での使用前に十分なテストを行ってください。
