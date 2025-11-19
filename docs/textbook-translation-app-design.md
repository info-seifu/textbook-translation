# 教科書翻訳アプリ 設計書

## 📋 プロジェクト概要

### 目的
Google Gemini APIを活用し、日本語教科書（横書き・縦書き）を多言語に翻訳するWebアプリケーションの開発

### 主要機能
- PDFファイルのアップロードと解析（Gemini使用）
- OCR + 図解抽出（Gemini 2.5 Pro / 3.0 Pro 切り替え可能）
- 多言語翻訳（Gemini Flash / Claude Sonnet選択可能）
- 図解・画像を含めたレイアウト保持
- 翻訳結果のダウンロード（Markdown/HTML/PDF）
- ローカル実行対応（Supabase不要）

### ターゲットユーザー
- 日本語教育関係者
- 教材翻訳が必要な教育機関
- 多言語対応教材を作成したい出版社

---

## 🏗️ アーキテクチャ概要

### 処理フロー

```
┌─────────────┐
│  PDF入力    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Gemini 2.5/3.0 Pro                  │
│ - OCR（日本語テキスト抽出）         │
│ - 図解検出・切り取り                │
│ - レイアウト解析                    │
│ - 書字方向自動判定                  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 日本語マークダウン（マスター）      │
│ - テキストコンテンツ                │
│ - 図解参照・配置情報                │
│ - メタデータ（レイアウト情報等）    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 翻訳エンジン（選択可能）            │
│ ┌─────────────────────────────────┐ │
│ │ Option 1: Gemini 2.0 Flash      │ │
│ │ - 高速・低コスト                │ │
│ │ - マルチモーダル統合性          │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Option 2: Claude Sonnet (推奨)  │ │
│ │ - 高品質・自然な翻訳            │ │
│ │ - 専門用語の一貫性              │ │
│ └─────────────────────────────────┘ │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 多言語マークダウン                  │
│ - en / zh / ko / etc.               │
│ - 図解埋め込み                      │
│ - HTML/PDF出力                      │
└─────────────────────────────────────┘
```

### 設計の核心原則

1. **マスターファイル方式**
   - OCRは1回のみ実行（コスト削減）
   - 日本語マークダウンをマスターとして保存
   - 全言語が同じソースから生成（一貫性保証）

2. **モジュラーアーキテクチャ**
   - OCR処理と翻訳処理を完全分離
   - 翻訳エンジンの切り替え可能性
   - 後から新言語追加が容易

3. **品質優先**
   - Gemini 2.5/3.0 ProでOCR精度向上
   - 書字方向自動判定（縦書き・横書き・混在を自動認識）
   - 翻訳エンジン選択で品質とコストのバランス調整

4. **柔軟なデプロイ**
   - ローカル実行対応（JSONベースDB）
   - Supabase対応（本番環境）
   - 環境変数で簡単に切り替え可能

---

## 🛠️ 技術スタック

### バックエンド
- **Python 3.10+**
- **Google Gemini API**
  - Gemini 2.5 Pro: `gemini-2.5-pro` (無料枠あり)
  - Gemini 3.0 Pro: `gemini-3-pro-preview` (課金必要、高精度)
  - Gemini 2.5 Flash: `gemini-2.5-flash` (翻訳用、高速・低コスト)
  - 環境変数 `USE_GEMINI_3` で2.5/3.0を切り替え
- **Anthropic Claude API** - 翻訳（オプション、推奨）
  - `claude-sonnet-4-5-20250929`
- **FastAPI** - APIサーバー + WebUI
- **Pillow / pdf2image** - PDF画像化
- **Markdown / WeasyPrint** - HTML/PDF生成

### フロントエンド
- **Next.js 14+** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** - UIコンポーネント

### インフラ・ストレージ

#### ローカル実行モード（開発・テスト用）
- **JSONベースDB** - `storage/database.json`
- **ローカルファイルストレージ** - `storage/pdfs/`, `storage/documents/`, `storage/figures/`
- Supabase不要で即座に動作可能

#### 本番環境モード
- **Vercel** - フロントエンドホスティング
- **Supabase** - PostgreSQL データベース
- **Supabase Storage** - PDF/画像保存
- **Docker** - バックエンド実行環境（オプション）

### 外部サービス
- **Google Gemini API** (必須)
- **Anthropic Claude API** (翻訳品質重視の場合)

---

## 📊 データベーススキーマ

> **Note**: 以下のスキーマは本番環境（Supabase使用時）のものです。
> ローカル実行時は `storage/database.json` にJSON形式で保存され、同じデータ構造を持ちます。

### translation_jobs テーブル
```sql
CREATE TABLE translation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),

    -- ファイル情報
    original_filename TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    page_count INTEGER,

    -- OCR結果
    japanese_markdown_url TEXT,  -- マスターファイル
    layout_metadata JSONB,        -- レイアウト情報
    figures_data JSONB,            -- 図解データ

    -- ステータス
    ocr_status TEXT CHECK (ocr_status IN ('pending', 'processing', 'completed', 'failed')),
    ocr_error TEXT,

    -- タイムスタンプ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_translation_jobs_user_id ON translation_jobs(user_id);
CREATE INDEX idx_translation_jobs_ocr_status ON translation_jobs(ocr_status);
```

### translation_outputs テーブル
```sql
CREATE TABLE translation_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES translation_jobs(id) ON DELETE CASCADE,

    -- 翻訳設定
    target_language TEXT NOT NULL,  -- 'en', 'zh', 'ko', etc.
    translator_engine TEXT CHECK (translator_engine IN ('gemini', 'claude')),

    -- 翻訳結果
    translated_markdown_url TEXT,
    html_url TEXT,
    pdf_url TEXT,

    -- ステータス
    status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,

    -- メタデータ
    translation_duration_seconds REAL,
    token_count INTEGER,
    cost_estimate REAL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_translation_outputs_job_id ON translation_outputs(job_id);
CREATE INDEX idx_translation_outputs_status ON translation_outputs(status);
```

### figures テーブル
```sql
CREATE TABLE figures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES translation_jobs(id) ON DELETE CASCADE,

    -- 図解情報
    page_number INTEGER NOT NULL,
    figure_number INTEGER NOT NULL,
    image_url TEXT NOT NULL,

    -- 位置情報
    bounding_box JSONB,  -- {x, y, width, height}

    -- メタデータ
    description TEXT,    -- Geminiが生成した説明
    extracted_text TEXT, -- 図解内のテキスト

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_figures_job_id ON figures(job_id);
```

### ローカルDB/ストレージ機能（実装済み）

#### ローカルデータベース（local_db.py）

Supabase不要でアプリを動作させるためのJSONベースDB。

**特徴**:
- `storage/database.json` に全データを保存
- Supabase互換のAPI（`table()`, `insert()`, `select()`, `update()`, `eq()`）
- スレッドセーフ
- 自動的にID、タイムスタンプを付与

**使用例**:
```python
from app.utils.local_db import get_local_db

db = get_local_db()

# INSERT
db.table('translation_jobs').insert({
    'original_filename': 'sample.pdf',
    'pdf_url': 'path/to/pdf',
    'ocr_status': 'pending'
}).execute()

# SELECT
job = db.table('translation_jobs').select('*').eq('id', job_id).single().execute()

# UPDATE
db.table('translation_jobs').update({
    'ocr_status': 'completed'
}).eq('id', job_id).execute()
```

#### ローカルストレージ（local_storage.py）

Supabase Storageの代わりにローカルファイルシステムを使用。

**ディレクトリ構造**:
```
storage/
├── database.json        # JSONベースDB
├── pdfs/               # アップロードされたPDF
│   └── {job_id}/
│       └── original.pdf
├── documents/          # マークダウンファイル
│   └── {job_id}/
│       ├── master_ja.md
│       ├── translated_en.md
│       └── translated_zh.md
└── figures/            # 抽出された図解
    └── {job_id}/
        ├── page1_fig1.png
        └── page1_fig2.png
```

**使用例**:
```python
from app.utils.local_storage import get_local_storage

storage = get_local_storage()

# アップロード
storage.from_('pdfs').upload(
    path=f"{job_id}/original.pdf",
    content=pdf_bytes
)

# ダウンロード
content = storage.from_('documents').download(
    path=f"{job_id}/master_ja.md"
)

# 公開URL取得（ローカルの場合はfile://パス）
url = storage.from_('figures').get_public_url(
    path=f"{job_id}/page1_fig1.png"
)
```

#### 環境変数による切り替え

```python
# app/utils/supabase_client.py

if settings.SUPABASE_URL:
    # Supabase使用
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
else:
    # ローカルDB/ストレージ使用
    supabase = LocalSupabaseClient()  # local_db + local_storage のラッパー
```

---

## 🔧 主要コンポーネント設計

### 1. PDF → OCR（Gemini 2.0 Flash Thinking）

#### 1.1 PDF前処理
```python
# services/pdf_preprocessor.py

from pdf2image import convert_from_path
from PIL import Image
import io

def pdf_to_images(pdf_path: str, dpi: int = 300) -> list[bytes]:
    """
    PDFを高解像度画像に変換

    Args:
        pdf_path: PDFファイルパス
        dpi: 解像度（デフォルト300dpi）

    Returns:
        各ページの画像データ（PNG形式バイト列）
    """
    images = convert_from_path(pdf_path, dpi=dpi)

    image_bytes_list = []
    for img in images:
        # PNG形式でバイト列化
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        image_bytes_list.append(img_bytes.getvalue())

    return image_bytes_list
```

#### 1.2 Gemini OCR実行
```python
# services/gemini_ocr_service.py

import google.generativeai as genai
from typing import TypedDict
import base64

class OCRResult(TypedDict):
    page_number: int
    markdown_text: str
    figures: list[dict]
    layout_info: dict

class GeminiOCRService:
    """Gemini 2.5 ProによるOCRサービス"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro-latest')

    async def extract_page(
        self,
        image_bytes: bytes,
        page_number: int
    ) -> OCRResult:
        """
        1ページ分のOCR処理

        Args:
            image_bytes: ページ画像
            page_number: ページ番号

        Returns:
            OCR結果（テキスト、図解、レイアウト情報）
        """

        # プロンプト構築
        prompt = self._build_ocr_prompt()

        # 画像をBase64エンコード
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # Gemini API呼び出し
        response = await self.model.generate_content_async([
            {
                'mime_type': 'image/png',
                'data': image_b64
            },
            prompt
        ])

        # 結果パース
        return self._parse_response(response.text, page_number)

    def _build_ocr_prompt(self) -> str:
        """OCR用プロンプト生成"""

        return """
あなたは日本語教科書のOCR専門家です。以下の画像から情報を抽出してください。

# 抽出タスク

## 1. 書字方向の自動判定
まず、この教科書ページの書字方向を判定してください:
- **縦書き** (vertical): 右から左、上から下に読む
- **横書き** (horizontal): 左から右、上から下に読む
- **混在** (mixed): 部分的に異なる方向が混在（例: 見出しは横書き、本文は縦書き）

## 2. テキスト抽出
- 判定した書字方向に従って、**正しい読み順序**でテキストを抽出
- 見出し、本文、キャプション、注釈を区別
- ルビ（ふりがな）がある場合は `{本文|ルビ}` 形式で記録
- Markdown形式で構造化（見出しは #、## など）

## 3. 図解・画像の検出
- すべての図、表、写真、イラスト、グラフを検出
- 各図解について以下を記録:
  - **位置**: ページ内のおおよその座標 (x, y, width, height)
  - **種類**: photo/illustration/diagram/table/graph
  - **図内のテキスト**: キャプション、ラベル、凡例等
  - **簡潔な説明**: 図が何を示しているか

## 4. レイアウト情報
- 段組み数（1段、2段、3段等）
- テキストと図解の配置関係
- 特殊なレイアウト要素（囲み記事、コラム、注釈ボックス等）

# 出力フォーマット

以下のJSON形式で出力してください:

```json
{
  "detected_writing_mode": "vertical|horizontal|mixed",
  "markdown_text": "抽出されたテキスト（Markdown形式）",
  "figures": [
    {
      "id": 1,
      "position": {"x": 100, "y": 200, "width": 400, "height": 300},
      "type": "photo|illustration|diagram|table|graph",
      "description": "図の説明",
      "extracted_text": "図内のテキスト（キャプション等）"
    }
  ],
  "layout_info": {
    "primary_direction": "vertical|horizontal",
    "columns": 1,
    "has_ruby": true|false,
    "special_elements": ["囲み記事", "注釈"],
    "mixed_regions": [
      {
        "region": "header",
        "direction": "horizontal"
      }
    ]
  }
}
```

# 重要な注意事項

1. **読み順序の正確性**: 書字方向を正しく判定し、その方向に従って読み順序を厳密に守ること
2. **図解の位置精度**: 図解の位置を可能な限り正確に記録すること
3. **ルビ・特殊記号**: ルビ、縦中横、特殊記号も正確に抽出すること
4. **レイアウトの忠実性**: 元のレイアウト構造（見出し階層、段落分け等）を維持すること
"""

    def _parse_response(self, response_text: str, page_number: int) -> OCRResult:
        """Gemini応答をパース"""

        import json
        import re

        # JSONブロックを抽出
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)

        if not json_match:
            raise ValueError("Failed to parse Gemini response")

        data = json.loads(json_match.group(1))

        return OCRResult(
            page_number=page_number,
            markdown_text=data['markdown_text'],
            figures=data.get('figures', []),
            layout_info=data.get('layout_info', {})
        )

    async def extract_figures_from_image(
        self,
        image_bytes: bytes,
        figure_positions: list[dict]
    ) -> list[bytes]:
        """
        図解を画像から切り取り

        Args:
            image_bytes: ページ全体の画像
            figure_positions: 図解の位置情報リスト

        Returns:
            切り取られた図解画像のリスト
        """
        from PIL import Image
        import io

        # 画像を開く
        img = Image.open(io.BytesIO(image_bytes))

        cropped_figures = []

        for fig_pos in figure_positions:
            # 位置情報取得
            box = fig_pos['position']

            # 切り取り
            cropped = img.crop((
                box['x'],
                box['y'],
                box['x'] + box['width'],
                box['y'] + box['height']
            ))

            # バイト列化
            cropped_bytes = io.BytesIO()
            cropped.save(cropped_bytes, format='PNG')
            cropped_figures.append(cropped_bytes.getvalue())

        return cropped_figures
```

#### 1.3 OCRオーケストレーション
```python
# services/ocr_orchestrator.py

from typing import List
import asyncio

class OCROrchestrator:
    """OCR処理全体の管理"""

    def __init__(self, gemini_service: GeminiOCRService, supabase_client):
        self.gemini = gemini_service
        self.supabase = supabase_client

    async def process_pdf(
        self,
        job_id: str,
        pdf_path: str
    ) -> str:
        """
        PDF全体のOCR処理

        Returns:
            日本語マークダウンのURL
        """

        # 1. PDFを画像化
        page_images = pdf_to_images(pdf_path)

        # 2. 各ページをOCR（並列処理）
        ocr_tasks = [
            self.gemini.extract_page(img, i+1)
            for i, img in enumerate(page_images)
        ]

        ocr_results = await asyncio.gather(*ocr_tasks)

        # 3. マークダウン統合
        full_markdown = self._merge_markdown(ocr_results)

        # 4. 図解を切り取ってStorageに保存
        await self._process_figures(job_id, page_images, ocr_results)

        # 5. マスターマークダウンをStorageに保存
        markdown_url = await self._save_markdown(job_id, full_markdown)

        # 6. メタデータをDBに保存
        await self._save_metadata(job_id, ocr_results)

        return markdown_url

    def _merge_markdown(self, ocr_results: List[OCRResult]) -> str:
        """各ページのマークダウンを統合"""

        markdown_parts = []

        for result in ocr_results:
            markdown_parts.append(f"# ページ {result['page_number']}\n\n")
            markdown_parts.append(result['markdown_text'])
            markdown_parts.append("\n\n")

            # 図解参照を挿入
            for fig in result['figures']:
                markdown_parts.append(
                    f"![図{fig['id']}](figures/page{result['page_number']}_fig{fig['id']}.png)\n\n"
                )
                if fig.get('description'):
                    markdown_parts.append(f"*{fig['description']}*\n\n")

        return ''.join(markdown_parts)

    async def _process_figures(
        self,
        job_id: str,
        page_images: list[bytes],
        ocr_results: List[OCRResult]
    ):
        """図解を切り取り、Storageに保存、DBに記録"""

        for result in ocr_results:
            page_num = result['page_number']
            page_image = page_images[page_num - 1]

            if not result['figures']:
                continue

            # 図解を切り取り
            figure_images = await self.gemini.extract_figures_from_image(
                page_image,
                result['figures']
            )

            # 各図解を保存
            for fig, fig_img in zip(result['figures'], figure_images):
                # Supabase Storageに保存
                file_path = f"{job_id}/figures/page{page_num}_fig{fig['id']}.png"
                image_url = self.supabase.storage.from_('figures').upload(
                    file_path,
                    fig_img
                )

                # DBに記録
                self.supabase.table('figures').insert({
                    'job_id': job_id,
                    'page_number': page_num,
                    'figure_number': fig['id'],
                    'image_url': image_url,
                    'bounding_box': fig['position'],
                    'description': fig.get('description'),
                    'extracted_text': fig.get('extracted_text')
                }).execute()

    async def _save_markdown(self, job_id: str, markdown: str) -> str:
        """マスターマークダウンをStorageに保存"""

        file_path = f"{job_id}/master_ja.md"
        url = self.supabase.storage.from_('documents').upload(
            file_path,
            markdown.encode('utf-8')
        )
        return url

    async def _save_metadata(self, job_id: str, ocr_results: List[OCRResult]):
        """レイアウト情報等をDBに保存"""

        layout_metadata = {
            'page_count': len(ocr_results),
            'pages': [r['layout_info'] for r in ocr_results]
        }

        self.supabase.table('translation_jobs').update({
            'layout_metadata': layout_metadata,
            'page_count': len(ocr_results),
            'ocr_status': 'completed'
        }).eq('id', job_id).execute()
```

---

### 2. 翻訳エンジン（選択可能）

#### 2.1 翻訳サービス抽象化
```python
# services/translator_base.py

from abc import ABC, abstractmethod

class TranslatorBase(ABC):
    """翻訳エンジンの基底クラス"""

    @abstractmethod
    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: dict = None
    ) -> str:
        """
        テキスト翻訳

        Args:
            source_text: 日本語マークダウン
            target_language: 翻訳先言語コード (en, zh, ko, etc.)
            context: 追加コンテキスト（レイアウト情報等）

        Returns:
            翻訳されたマークダウン
        """
        pass
```

#### 2.2 Claude翻訳実装
```python
# services/claude_translator.py

from anthropic import AsyncAnthropic
from .translator_base import TranslatorBase

class ClaudeTranslator(TranslatorBase):
    """Claude Sonnetによる翻訳"""

    LANGUAGE_NAMES = {
        'en': 'English',
        'zh': '简体中文',
        'zh-TW': '繁體中文',
        'ko': '한국어',
        'vi': 'Tiếng Việt',
        'th': 'ไทย',
        'es': 'Español',
        'fr': 'Français'
    }

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: dict = None
    ) -> str:
        """Claude Sonnetで翻訳"""

        target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

        prompt = f"""
あなたは教育教材の翻訳専門家です。

以下の日本語教科書のマークダウンテキストを{target_lang_name}に翻訳してください。

# 翻訳時の重要事項

1. **教育的文脈の保持**
   - 学習者が理解しやすい表現を使用
   - 専門用語は正確に翻訳

2. **フォーマットの保持**
   - Markdown形式をそのまま維持
   - 見出し（#）、リスト、強調等の構造を保持
   - 図解参照（`![図1](...)`）は変更しない

3. **一貫性**
   - 用語の統一
   - 文体の統一

4. **図解参照**
   - 「図1参照」などの表現は翻訳するが、画像リンクは変更しない

5. **特殊記号**
   - ルビ（`{{本文|ルビ}}`）は翻訳後削除または翻訳

# 翻訳対象テキスト

{source_text}

# 出力

{target_lang_name}に翻訳されたマークダウンのみを出力してください。説明や注釈は不要です。
"""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        return response.content[0].text
```

#### 2.3 Gemini翻訳実装
```python
# services/gemini_translator.py

import google.generativeai as genai
from .translator_base import TranslatorBase

class GeminiTranslator(TranslatorBase):
    """Gemini 2.5 Flashによる翻訳"""

    LANGUAGE_NAMES = {
        'en': 'English',
        'zh': 'Simplified Chinese (简体中文)',
        'zh-TW': 'Traditional Chinese (繁體中文)',
        'ko': 'Korean (한국어)',
        'vi': 'Vietnamese (Tiếng Việt)',
        'th': 'Thai (ไทย)',
        'es': 'Spanish (Español)',
        'fr': 'French (Français)'
    }

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-latest')

    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: dict = None
    ) -> str:
        """Gemini Flashで翻訳"""

        target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

        prompt = f"""
You are an expert translator specializing in educational materials.

Translate the following Japanese textbook markdown content into {target_lang_name}.

# Translation Guidelines

1. **Maintain Educational Context**
   - Use clear, student-friendly language
   - Translate technical terms accurately

2. **Preserve Formatting**
   - Keep all Markdown formatting intact
   - Maintain headings (#), lists, emphasis, etc.
   - DO NOT modify image references (`![Figure 1](...)`)

3. **Consistency**
   - Use consistent terminology throughout
   - Maintain consistent tone

4. **Figure References**
   - Translate phrases like "See Figure 1" but keep image links unchanged

5. **Special Notations**
   - Ruby annotations (`{{text|ruby}}`) should be removed or adapted as appropriate

# Source Text

{source_text}

# Output

Provide ONLY the translated markdown in {target_lang_name}. No explanations or comments.
"""

        response = await self.model.generate_content_async(prompt)
        return response.text
```

#### 2.4 翻訳オーケストレーション
```python
# services/translation_orchestrator.py

from .claude_translator import ClaudeTranslator
from .gemini_translator import GeminiTranslator
from typing import Literal

TranslatorEngine = Literal['claude', 'gemini']

class TranslationOrchestrator:
    """翻訳処理の管理"""

    def __init__(
        self,
        claude_api_key: str,
        gemini_api_key: str,
        supabase_client
    ):
        self.claude = ClaudeTranslator(claude_api_key)
        self.gemini = GeminiTranslator(gemini_api_key)
        self.supabase = supabase_client

    async def translate_document(
        self,
        job_id: str,
        target_language: str,
        translator_engine: TranslatorEngine = 'claude'
    ) -> str:
        """
        文書全体を翻訳

        Args:
            job_id: 翻訳ジョブID
            target_language: 翻訳先言語
            translator_engine: 使用する翻訳エンジン

        Returns:
            翻訳済みマークダウンのURL
        """

        # 1. マスターマークダウンを取得
        job = self.supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()
        master_md_url = job.data['japanese_markdown_url']
        master_text = self._download_text(master_md_url)

        # 2. 翻訳エンジン選択
        translator = self.claude if translator_engine == 'claude' else self.gemini

        # 3. 翻訳実行
        translated_text = await translator.translate(
            master_text,
            target_language,
            context=job.data.get('layout_metadata')
        )

        # 4. 翻訳結果を保存
        translated_url = await self._save_translation(
            job_id,
            target_language,
            translated_text
        )

        # 5. DBに記録
        await self._record_translation(
            job_id,
            target_language,
            translator_engine,
            translated_url
        )

        return translated_url

    def _download_text(self, url: str) -> str:
        """Storage からテキストダウンロード"""
        # 実装省略
        pass

    async def _save_translation(
        self,
        job_id: str,
        language: str,
        text: str
    ) -> str:
        """翻訳をStorageに保存"""

        file_path = f"{job_id}/translated_{language}.md"
        url = self.supabase.storage.from_('documents').upload(
            file_path,
            text.encode('utf-8')
        )
        return url

    async def _record_translation(
        self,
        job_id: str,
        language: str,
        engine: TranslatorEngine,
        translated_url: str
    ):
        """翻訳結果をDBに記録"""

        self.supabase.table('translation_outputs').insert({
            'job_id': job_id,
            'target_language': language,
            'translator_engine': engine,
            'translated_markdown_url': translated_url,
            'status': 'completed'
        }).execute()
```

---

### 3. API設計

#### 3.1 PDFアップロード
```python
# api/upload.py

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from uuid import uuid4

router = APIRouter()

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    PDFアップロード＆OCR開始

    Args:
        file: PDFファイル

    Returns:
        ジョブID

    Note:
        書字方向（縦書き/横書き）はGeminiが自動判定します
    """

    # ジョブID生成
    job_id = str(uuid4())

    # PDFをStorageに保存
    pdf_path = f"{job_id}/original.pdf"
    pdf_url = supabase.storage.from_('pdfs').upload(pdf_path, file.file)

    # DBにジョブレコード作成
    supabase.table('translation_jobs').insert({
        'id': job_id,
        'original_filename': file.filename,
        'pdf_url': pdf_url,
        'ocr_status': 'pending'
    }).execute()

    # バックグラウンドでOCR開始
    background_tasks.add_task(
        run_ocr_task,
        job_id,
        pdf_path
    )

    return {
        'job_id': job_id,
        'status': 'pending',
        'message': 'OCR processing started (writing direction will be auto-detected)'
    }

async def run_ocr_task(job_id: str, pdf_path: str):
    """バックグラウンドOCRタスク"""

    try:
        # OCR実行（書字方向は自動判定）
        orchestrator = OCROrchestrator(gemini_service, supabase)
        markdown_url = await orchestrator.process_pdf(job_id, pdf_path)

        # ステータス更新
        supabase.table('translation_jobs').update({
            'ocr_status': 'completed',
            'japanese_markdown_url': markdown_url
        }).eq('id', job_id).execute()

    except Exception as e:
        # エラー記録
        supabase.table('translation_jobs').update({
            'ocr_status': 'failed',
            'ocr_error': str(e)
        }).eq('id', job_id).execute()
```

#### 3.2 翻訳開始
```python
# api/translate.py

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

class TranslateRequest(BaseModel):
    job_id: str
    target_language: str  # 'en', 'zh', 'ko', etc.
    translator_engine: TranslatorEngine = 'claude'  # デフォルトClaude

@router.post("/translate")
async def start_translation(
    request: TranslateRequest,
    background_tasks: BackgroundTasks
):
    """
    翻訳開始

    Args:
        job_id: OCR完了済みのジョブID
        target_language: 翻訳先言語
        translator_engine: 'claude' または 'gemini'

    Returns:
        翻訳出力ID
    """

    # ジョブステータス確認
    job = supabase.table('translation_jobs').select('*').eq('id', request.job_id).single().execute()

    if job.data['ocr_status'] != 'completed':
        return {
            'error': 'OCR not completed yet',
            'ocr_status': job.data['ocr_status']
        }, 400

    # 翻訳出力レコード作成
    output_id = str(uuid4())
    supabase.table('translation_outputs').insert({
        'id': output_id,
        'job_id': request.job_id,
        'target_language': request.target_language,
        'translator_engine': request.translator_engine,
        'status': 'pending'
    }).execute()

    # バックグラウンドで翻訳開始
    background_tasks.add_task(
        run_translation_task,
        output_id,
        request.job_id,
        request.target_language,
        request.translator_engine
    )

    return {
        'output_id': output_id,
        'status': 'pending',
        'message': 'Translation started'
    }

async def run_translation_task(
    output_id: str,
    job_id: str,
    target_language: str,
    translator_engine: TranslatorEngine
):
    """バックグラウンド翻訳タスク"""

    try:
        orchestrator = TranslationOrchestrator(
            claude_api_key=settings.CLAUDE_API_KEY,
            gemini_api_key=settings.GEMINI_API_KEY,
            supabase_client=supabase
        )

        translated_url = await orchestrator.translate_document(
            job_id,
            target_language,
            translator_engine
        )

        supabase.table('translation_outputs').update({
            'status': 'completed',
            'translated_markdown_url': translated_url
        }).eq('id', output_id).execute()

    except Exception as e:
        supabase.table('translation_outputs').update({
            'status': 'failed',
            'error_message': str(e)
        }).eq('id', output_id).execute()
```

#### 3.3 ステータス確認
```python
# api/status.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    ジョブステータス取得
    """

    job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

    # 翻訳出力一覧も取得
    outputs = supabase.table('translation_outputs').select('*').eq('job_id', job_id).execute()

    return {
        'job': job.data,
        'translations': outputs.data
    }

@router.get("/outputs/{output_id}")
async def get_output_status(output_id: str):
    """
    翻訳出力ステータス取得
    """

    output = supabase.table('translation_outputs').select('*').eq('id', output_id).single().execute()

    return output.data
```

#### 3.4 ダウンロード
```python
# api/download.py

from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse

router = APIRouter()

@router.get("/download/{output_id}/markdown")
async def download_markdown(output_id: str):
    """
    翻訳済みマークダウンをダウンロード
    """

    output = supabase.table('translation_outputs').select('*').eq('id', output_id).single().execute()

    if output.data['status'] != 'completed':
        return {'error': 'Translation not completed'}, 400

    # Storageからダウンロード
    markdown_content = supabase.storage.from_('documents').download(
        output.data['translated_markdown_url']
    )

    return StreamingResponse(
        io.BytesIO(markdown_content),
        media_type='text/markdown',
        headers={
            'Content-Disposition': f'attachment; filename="translated_{output.data["target_language"]}.md"'
        }
    )
```

---

## 📂 ファイル構造

```
textbook-translation/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPIエントリーポイント
│   │   ├── config.py                        # 設定管理
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py                    # PDFアップロード
│   │   │   ├── translate.py                 # 翻訳開始
│   │   │   ├── status.py                    # ステータス確認
│   │   │   └── download.py                  # ダウンロード
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_preprocessor.py          # PDF前処理
│   │   │   ├── gemini_ocr_service.py        # Gemini OCR
│   │   │   ├── ocr_orchestrator.py          # OCR全体管理
│   │   │   ├── translator_base.py           # 翻訳基底クラス
│   │   │   ├── claude_translator.py         # Claude翻訳
│   │   │   ├── gemini_translator.py         # Gemini翻訳
│   │   │   └── translation_orchestrator.py  # 翻訳全体管理
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py                   # Pydanticモデル
│   │   │
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── supabase_client.py           # Supabaseクライアント
│   │   │   ├── local_db.py                  # ローカルDB（実装済み）
│   │   │   ├── local_storage.py             # ローカルストレージ（実装済み）
│   │   │   ├── retry.py                     # リトライ機能（実装済み）
│   │   │   ├── logging_config.py            # ロギング設定（実装済み）
│   │   │   └── error_handlers.py            # エラーハンドリング
│   │   │
│   │   ├── static/                          # WebUI用静的ファイル（実装済み）
│   │   ├── templates/                       # WebUI用HTMLテンプレート（実装済み）
│   │   └── exceptions.py                    # カスタム例外（実装済み）
│   │
│   ├── tests/                               # テストコード（実装済み）
│   │   ├── test_gemini_ocr_service.py
│   │   ├── test_gemini_translator.py
│   │   ├── test_claude_translator.py
│   │   ├── test_api_upload.py
│   │   ├── test_api_status.py
│   │   └── test_ocr_orchestrator.py
│   │
│   ├── launcher.py                          # スタンドアロン起動スクリプト（実装済み）
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                         # トップページ（実装済み）
│   │   ├── layout.tsx                       # レイアウト（実装済み）
│   │   ├── upload/
│   │   │   └── page.tsx                     # アップロードページ（実装済み）
│   │   └── jobs/
│   │       └── [id]/
│   │           └── page.tsx                 # ジョブ詳細（実装済み）
│   │
│   ├── components/
│   │   ├── ui/                              # shadcn/ui
│   │   ├── FileUploader.tsx                 # ファイルアップローダー
│   │   ├── OCRProgress.tsx                  # OCR進捗表示
│   │   ├── TranslationProgress.tsx          # 翻訳進捗表示
│   │   ├── TranslationEngineSelector.tsx    # エンジン選択
│   │   └── MarkdownViewer.tsx               # マークダウン表示
│   │
│   ├── lib/
│   │   ├── supabase.ts                      # Supabaseクライアント
│   │   └── api.ts                           # APIクライアント
│   │
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
│
├── docs/
│   ├── textbook-translation-app-design.md   # この設計書
│   ├── api-reference.md                     # API仕様
│   └── user-guide.md                        # ユーザーガイド
│
├── samples/
│   ├── pdf/
│   │   ├── horizontal/                      # 横書きサンプル
│   │   └── vertical/                        # 縦書きサンプル
│   └── README.md
│
├── tests/
│   ├── test_gemini_ocr.py
│   ├── test_claude_translator.py
│   ├── test_gemini_translator.py
│   └── test_integration.py
│
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 🚀 実装状況

### ✅ Phase 1: 基本機能（完了）

#### 達成内容
- ✅ PDF → OCR → 日本語マークダウン生成
- ✅ 日本語マークダウン → 多言語翻訳
- ✅ WebUI（FastAPI内蔵）

#### 完了タスク
- [x] 要件定義・設計書作成
- [x] ローカルDB/ストレージ実装（Supabase不要）
- [x] バックエンド基盤構築（FastAPI + WebUI）
- [x] Gemini OCR実装（2.5/3.0切り替え対応）
- [x] Claude翻訳実装
- [x] フロントエンド基本UI（Next.js）
- [x] 統合テスト

### ✅ Phase 2: エンジン選択＆多言語対応（完了）

#### 達成内容
- ✅ Gemini翻訳実装
- ✅ Gemini 2.5/3.0切り替え機能
- ✅ 多言語対応（英語、中国語、韓国語等）

#### 完了タスク
- [x] Gemini翻訳実装
- [x] エンジン切り替え機能（`USE_GEMINI_3`環境変数）
- [x] 複数言語サポート
- [x] バッチ翻訳機能

### ✅ Phase 3: 品質向上＆最適化（完了）

#### 達成内容
- ✅ エラーハンドリング強化
- ✅ リトライ機能実装
- ✅ HTML/PDF出力機能

#### 完了タスク
- [x] リトライ機能（exponential backoff）
- [x] カスタム例外実装
- [x] ロギング設定
- [x] HTML/PDF生成機能
- [x] テストコード整備

### 🔄 Phase 4: 追加機能・改善（進行中）

#### 残タスク
- [ ] フロントエンド完成（Next.js）
  - [ ] 翻訳結果表示ページ
  - [ ] ダウンロードUI
  - [ ] エラー表示改善
- [ ] 本番環境デプロイ準備
  - [ ] Supabase統合テスト
  - [ ] Vercelデプロイ設定
  - [ ] Docker設定

---

## ⚙️ 設定ファイル

### 環境変数（.env）

#### 必須設定
```bash
# Google Gemini API (必須)
GEMINI_API_KEY=your_gemini_api_key

# Anthropic Claude API (必須)
CLAUDE_API_KEY=your_claude_api_key
```

#### オプショナル設定（ローカル実行時は不要）
```bash
# Supabase（本番環境で使用する場合のみ設定）
# ローカル環境ではJSONベースのデータベースを使用するため不要
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=
```

#### バックエンド設定
```bash
# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# File Upload
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=uploads

# Gemini バージョン選択
# USE_GEMINI_3=true → Gemini 3.0 Pro (課金必要、高精度)
# USE_GEMINI_3=false → Gemini 2.5 Pro (無料枠あり、デフォルト)
USE_GEMINI_3=false
```

#### フロントエンド設定（Next.js使用時）
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co  # オプショナル
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key  # オプショナル
```

### requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
google-genai>=1.0.0                # Gemini SDK (最新版)
anthropic==0.18.0
pdf2image==1.17.0
Pillow==10.2.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
httpx==0.26.0
aiofiles==23.2.1

# HTML/PDF generation
markdown==3.5.1
weasyprint==60.2
jinja2==3.1.2

# For testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# For Windows .exe build (オプショナル)
pyinstaller==6.3.0
```

---

## 🧪 テスト戦略

### ユニットテスト

```python
# tests/test_gemini_ocr.py

import pytest
from app.services.gemini_ocr_service import GeminiOCRService

@pytest.mark.asyncio
async def test_extract_page_vertical():
    """縦書きページのOCRテスト"""

    service = GeminiOCRService(api_key=os.getenv('GEMINI_API_KEY'))

    # サンプル画像読み込み
    with open('tests/fixtures/vertical_sample.png', 'rb') as f:
        image_bytes = f.read()

    result = await service.extract_page(image_bytes, page_number=1, is_vertical=True)

    assert result['page_number'] == 1
    assert len(result['markdown_text']) > 0
    assert result['layout_info']['writing_mode'] == 'vertical'

@pytest.mark.asyncio
async def test_extract_figures():
    """図解抽出テスト"""

    service = GeminiOCRService(api_key=os.getenv('GEMINI_API_KEY'))

    # テスト実装...
```

```python
# tests/test_claude_translator.py

import pytest
from app.services.claude_translator import ClaudeTranslator

@pytest.mark.asyncio
async def test_translate_to_english():
    """日本語→英語翻訳テスト"""

    translator = ClaudeTranslator(api_key=os.getenv('CLAUDE_API_KEY'))

    source_text = """
# 第1章 はじめに

これは教科書のサンプルテキストです。

![図1](figures/fig1.png)
"""

    result = await translator.translate(source_text, target_language='en')

    assert 'Chapter 1' in result or '# Introduction' in result
    assert '![Figure 1]' in result or '![Fig 1]' in result
```

### 統合テスト

```python
# tests/test_integration.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_workflow():
    """完全ワークフローテスト"""

    async with AsyncClient(base_url="http://localhost:8000") as client:
        # 1. PDFアップロード
        with open('tests/fixtures/sample.pdf', 'rb') as f:
            response = await client.post(
                '/api/upload',
                files={'file': ('sample.pdf', f, 'application/pdf')},
                data={'is_vertical': 'true'}
            )

        assert response.status_code == 200
        job_id = response.json()['job_id']

        # 2. OCR完了待機
        for _ in range(60):  # 最大60秒待機
            response = await client.get(f'/api/jobs/{job_id}')
            if response.json()['job']['ocr_status'] == 'completed':
                break
            await asyncio.sleep(1)

        assert response.json()['job']['ocr_status'] == 'completed'

        # 3. 翻訳開始
        response = await client.post('/api/translate', json={
            'job_id': job_id,
            'target_language': 'en',
            'translator_engine': 'claude'
        })

        assert response.status_code == 200
        output_id = response.json()['output_id']

        # 4. 翻訳完了待機
        for _ in range(120):
            response = await client.get(f'/api/outputs/{output_id}')
            if response.json()['status'] == 'completed':
                break
            await asyncio.sleep(1)

        assert response.json()['status'] == 'completed'

        # 5. ダウンロード
        response = await client.get(f'/api/download/{output_id}/markdown')
        assert response.status_code == 200
        assert 'text/markdown' in response.headers['content-type']
```

---

## 💰 コスト試算

### Gemini API（OCR）
- **モデル**: gemini-2.5-pro-latest
- **料金**:
  - 入力: $1.25 / 1M tokens（画像含む）
  - 出力: $5.00 / 1M tokens
- **例**: 50ページPDF（画像50枚、各ページ約2,000トークン相当）
  - 入力: 100K tokens × $1.25 / 1M = $0.125
  - 出力: 10K tokens × $5.00 / 1M = $0.05
  - **合計**: **$0.175**

### 翻訳コスト比較

#### Claude Sonnet 4.5
- **入力**: $3.00 / 1M tokens
- **出力**: $15.00 / 1M tokens
- **例**: 50ページ（約10,000 tokens入力、10,000 tokens出力）
  - 入力: 10K × $3 / 1M = $0.03
  - 出力: 10K × $15 / 1M = $0.15
  - **合計**: **$0.18**

#### Gemini 2.5 Flash
- **入力**: $0.075 / 1M tokens
- **出力**: $0.30 / 1M tokens
- **例**: 50ページ（約10,000 tokens入力、10,000 tokens出力）
  - 入力: 10K × $0.075 / 1M = $0.00075
  - 出力: 10K × $0.30 / 1M = $0.003
  - **合計**: **$0.004**

### 総コスト試算（50ページ教科書）

| 処理 | コスト |
|------|--------|
| OCR（Gemini 2.5 Pro） | $0.175 |
| 翻訳（Claude Sonnet） | $0.18 |
| 翻訳（Gemini 2.5 Flash） | $0.004 |
| **合計（Claude使用時）** | **$0.355** |
| **合計（Gemini使用時）** | **$0.179** |

### 推奨戦略
- **品質重視**: OCR（Gemini 2.5 Pro） + 翻訳（Claude） = **$0.36/50p**
- **コスト重視**: OCR（Gemini 2.5 Pro） + 翻訳（Gemini 2.5 Flash） = **$0.18/50p**
- **ハイブリッド**: 初稿Gemini Flash → Claude校正

---

## 🔒 セキュリティ考慮事項

### ファイルアップロード
- MIMEタイプ検証
- ファイルサイズ制限（50MB）
- ウイルススキャン（将来的に）

### API認証
- Supabase Auth使用
- JWT トークン検証
- RLS（Row Level Security）設定

### データプライバシー
- アップロードPDF: 処理後30日で自動削除
- 個人情報保護法対応

---

## 📊 モニタリング

### メトリクス収集
- OCR成功率/失敗率
- 翻訳成功率/失敗率
- 平均処理時間
- APIコスト

### ログ管理
- 構造化ログ（JSON）
- エラートラッキング
- パフォーマンス監視

---

## 📖 今後の拡張計画

### Phase 4以降
- [ ] バッチ処理（複数PDF一括処理）
- [ ] ユーザー辞書機能
- [ ] HTML/PDF出力強化
- [ ] リアルタイムプレビュー
- [ ] 翻訳メモリ
- [ ] 協調編集機能

---

## 📝 まとめ

### 設計のポイント

1. **Markerからの脱却**
   - 縦書き・横書き・混在レイアウトに対応するためGemini採用
   - 書字方向の自動判定（ユーザー指定不要）
   - OCRと翻訳の完全分離

2. **マスターファイル方式**
   - 1回のOCRで複数言語対応
   - コスト削減と一貫性の両立

3. **翻訳エンジン選択**
   - Claude: 品質重視（推奨）
   - Gemini: コスト重視
   - ユーザーが選択可能

4. **拡張性**
   - 新言語追加が容易
   - 新翻訳エンジンの追加が容易
   - モジュラー設計

---

**作成日**: 2025年1月14日
**バージョン**: 2.0
**対象**: 教科書翻訳アプリ（Geminiベース）
**ステータス**: 設計完了、実装未着手
