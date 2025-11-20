# レイアウト保持型翻訳機能 設計書

## 📋 概要

### 目的
入力PDFの図表・レイアウトを保持したまま翻訳出力を生成する機能の実装

### 主要要件
1. **図表の抽出と保存**: 元PDFから図・表・画像を切り出して保存
2. **レイアウト情報の保持**: 図表の位置、章の構造を保持
3. **翻訳後の再構築**: HTMLとPDFで図表を元の位置（または章内の適切な位置）に配置
4. **縦書き→横書き対応**: 縦書きPDFから横書き翻訳への変換時、レイアウト調整を許容

---

## 🎯 設計原則

### 1. 章単位での構造保持
- 図表は必ず元の章内に配置
- 章をまたいだ移動は禁止
- 章内での位置調整は許容（縦書き→横書き変換時）

### 2. 段階的実装
- Phase 1から順に実装
- 各Phaseで独立した機能を提供
- 後続Phaseのための「仕込み」を最初から組み込む

### 3. 疎結合アーキテクチャ
- 画像抽出、HTML生成、PDF生成は独立したモジュール
- メタデータを介して連携
- 将来の拡張（目次対応など）を考慮した設計

---

## 📦 実装Phase

### Phase 1: PDF画像抽出と保存（MVP）

#### 目的
元PDFから図表を画像として抽出し、ファイルシステムに保存

#### 実装内容

**1.1 新規サービス: `pdf_image_extractor.py`**
```python
class PDFImageExtractor:
    """PDFから図表画像を抽出するサービス"""

    def extract_figures_from_pdf(
        self,
        pdf_path: str,
        figures_metadata: List[Dict],
        output_dir: str
    ) -> List[str]:
        """
        Args:
            pdf_path: 元PDFのパス
            figures_metadata: OCR結果から得た図表の座標情報
            output_dir: 画像保存先ディレクトリ

        Returns:
            保存した画像ファイルのパスリスト
        """
```

**技術選択**: PyMuPDF (fitz)
- 理由: 座標ベースの画像切り出しが容易、軽量、高速

**1.2 ストレージ構造**
```
storage/documents/{job_id}/
├── input.pdf
├── japanese_markdown.md
├── figures/
│   ├── page_1_fig_1.png
│   ├── page_1_fig_2.png
│   ├── page_2_fig_1.png
│   └── metadata.json
└── outputs/
    └── {output_id}/
        └── translated_{lang}.md
```

**1.3 メタデータフォーマット**
```json
{
  "figures": [
    {
      "id": "page_1_fig_1",
      "page": 1,
      "bbox": [100, 200, 400, 500],
      "type": "diagram",
      "caption": "システム構成図",
      "section_id": "chapter-1",
      "file_path": "figures/page_1_fig_1.png"
    }
  ]
}
```

**1.4 統合先: `ocr_orchestrator.py`**
- OCR完了後に画像抽出処理を実行
- 図表情報をメタデータに保存

#### 変更ファイル
- **新規**: `backend/app/services/pdf_image_extractor.py`
- **修正**: `backend/app/services/ocr_orchestrator.py`
- **修正**: `backend/requirements.txt` (PyMuPDF追加)

---

### Phase 2: Markdown生成の改善

#### 目的
図表参照を含むMarkdownを生成、将来の機能のための「仕込み」を実装

#### 実装内容

**2.1 見出しにID属性を付与**
```markdown
<h1 id="chapter-1">第1章 情報の表現</h1>

本文がここに...

![図1: システム構成図](figures/page_1_fig_1.png)
```

**2.2 セクションメタデータの拡張**
```json
{
  "sections": [
    {
      "id": "chapter-1",
      "title_ja": "第1章 情報の表現",
      "title_en": null,
      "original_pages": [1, 2],
      "translated_pages": null,
      "figures": ["page_1_fig_1", "page_2_fig_1"]
    }
  ]
}
```

**2.3 図表参照の挿入ロジック**
- OCR結果の図表位置情報を元に、適切な段落の後に図表参照を挿入
- 章の境界を超えて図表を配置しない

#### 変更ファイル
- **修正**: `backend/app/services/ocr_orchestrator.py`
- **修正**: `backend/app/models/schemas.py` (メタデータスキーマ拡張)

---

### Phase 3: HTML生成の改善

#### 目的
図表を含むHTMLを生成、レイアウトをCSSで制御

#### 実装内容

**3.1 図表配置のHTML生成**
```html
<section id="chapter-1">
  <h1>Chapter 1: Information Representation</h1>
  <p>Body text...</p>

  <figure class="embedded-figure">
    <img src="/api/figures/{job_id}/page_1_fig_1.png" alt="System Architecture">
    <figcaption>Figure 1: System Architecture</figcaption>
  </figure>

  <p>More text...</p>
</section>
```

**3.2 レイアウトCSS**
```css
/* 縦書き対応（入力が縦書きの場合） */
.vertical-text {
  writing-mode: vertical-rl;
}

/* 翻訳版は横書き統一 */
.translated-text {
  writing-mode: horizontal-tb;
}

/* 図表配置 */
.embedded-figure {
  margin: 2rem 0;
  text-align: center;
}

/* 改ページ制御（PDF用） */
.chapter-start {
  page-break-before: always;
}
```

**3.3 フォーマット問題の修正**
- 「Question 1」のフォントサイズを本文と同じに（見出しタグを使わない）
- 回答選択肢を横並びに（inline要素として配置）

#### 変更ファイル
- **修正**: `backend/app/services/html_generator.py`
- **新規**: `backend/app/templates/translated_document.html` (HTMLテンプレート)

---

### Phase 4: PDF生成の改善

#### 目的
WeasyPrintで図表を含むPDFを生成

#### 実装内容

**4.1 ページ番号の制御**
```css
@page {
  /* フッターにページ番号（要望に応じて） */
  @bottom-center {
    content: counter(page);
    font-size: 10pt;
  }

  /* 本文中の大きな"Page X"は表示しない（Markdown生成時に除外） */
}
```

**4.2 改ページ制御**
```css
.question-start {
  page-break-before: always;
}

.figure-container {
  page-break-inside: avoid;
}
```

**4.3 画像の埋め込み**
- 相対パス方式: 開発・プレビュー用
- Base64埋め込み: 配布用（将来実装）

#### 変更ファイル
- **修正**: `backend/app/services/pdf_generator.py`

---

### Phase 5: API/UI改善

#### 目的
画像配信エンドポイントとプレビューUIの追加

#### 実装内容

**5.1 画像配信API**
```python
@router.get("/api/figures/{job_id}/{filename}")
async def get_figure(job_id: str, filename: str):
    """図表画像を配信"""
    file_path = Path("storage/documents") / job_id / "figures" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404)

    return FileResponse(file_path, media_type="image/png")
```

**5.2 ジョブ詳細ページの改善**
- 翻訳結果プレビュー（図表込み）
- レイアウト確認UI

#### 変更ファイル
- **新規**: `backend/app/api/figures.py`
- **修正**: `backend/app/main.py` (ルーター登録)
- **修正**: `frontend/app/jobs/[id]/page.tsx`

---

### Phase 6: 目次機能（将来実装）

#### 目的
翻訳後のページ番号で目次を自動更新

#### 実装方針
- 2パス処理: 仮PDF生成 → ページ番号取得 → 目次更新 → 最終PDF生成
- Phase 2で保存したセクションメタデータを活用
- Phase 3で付与したID属性を活用

**実装は最後でOK（Phase 1-5が完了してから）**

---

## 🔧 技術的詳細

### 依存ライブラリの追加

```txt
# requirements.txt に追加
PyMuPDF==1.23.26  # PDF画像抽出
Pillow>=10.0.0    # 画像処理（既存で入っている可能性あり）
```

### 座標系の扱い

**PDFの座標系**:
- 左下が原点 (0, 0)
- 単位: ポイント (1pt = 1/72 inch)

**正規化座標**:
- 相対座標 (0.0 - 1.0) で保存
- ページサイズに依存しない
- 異なる出力フォーマットに対応

```python
def normalize_bbox(bbox, page_width, page_height):
    """座標を正規化"""
    x0, y0, x1, y1 = bbox
    return (
        x0 / page_width,
        y0 / page_height,
        x1 / page_width,
        y1 / page_height
    )
```

### 縦書き→横書き変換の考慮事項

**レイアウト調整の許容範囲**:
- ✅ 図表の位置変更（右→下など）
- ✅ テキストと図表の順序入れ替え
- ✅ 段組み数の変更
- ❌ 章をまたいだ移動

**実装上の対応**:
- セクションIDで章の境界を管理
- 図表には必ず `section_id` を紐付け
- HTML生成時にセクション内でのみ配置

---

## 📊 テスト戦略

### Phase 1 テスト
- **単体テスト**: `PDFImageExtractor` のメソッドテスト
- **統合テスト**: OCR → 画像抽出の一連の流れ
- **検証項目**:
  - 画像ファイルが正しく保存されるか
  - メタデータが正確か
  - 複数ページ、複数図表の処理

### Phase 2-5 テスト
- 各Phaseごとに既存テストを更新
- E2Eテスト: PDF アップロード → 図表込み出力

---

## 🚀 実装スケジュール

| Phase | 内容 | 工数見積 |
|-------|------|---------|
| Phase 1 | PDF画像抽出 | 4-6時間 |
| Phase 2 | Markdown改善 | 3-4時間 |
| Phase 3 | HTML生成改善 | 4-5時間 |
| Phase 4 | PDF生成改善 | 3-4時間 |
| Phase 5 | API/UI改善 | 3-4時間 |
| **合計** | **MVP実装** | **17-23時間** |

Phase 6（目次機能）は別途検討（8-12時間見込み）

---

## 📝 備考

### 設計上の「仕込み」

Phase 1-5の実装時に、将来の拡張（Phase 6など）のために以下を組み込む：

1. **見出しのID属性**: 最初から付与
2. **セクションメタデータ**: 構造化して保存
3. **アンカーポイント**: HTML内に埋め込み

これにより、目次機能や他の拡張機能を後から追加しても既存コードへの影響を最小化できる。
