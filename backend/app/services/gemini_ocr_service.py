"""
Gemini OCRサービス (PDF直接送信版)
"""
from google import genai
from google.genai import types
from typing import List
import json
import re
import logging
import base64

from app.models.schemas import OCRResult, FigureData, LayoutInfo, FigurePosition
from app.utils.retry import async_retry
from app.exceptions import OCRException, APIRateLimitException
from app.config import settings

logger = logging.getLogger(__name__)


class GeminiOCRService:
    """Gemini OCRサービス (PDF直接送信対応)"""

    def __init__(self, api_key: str):
        # Gemini SDK使用
        self.client = genai.Client(api_key=api_key)
        self.model = settings.gemini_ocr_model

    @async_retry(
        max_retries=3,
        base_delay=2.0,
        max_delay=60.0,
        exceptions=(Exception,),
        rate_limit_exceptions=(APIRateLimitException,)
    )
    async def extract_from_pdf(
        self,
        pdf_path: str
    ) -> List[OCRResult]:
        """
        PDF全体のOCR処理（PDF直接送信）

        Args:
            pdf_path: PDFファイルパス

        Returns:
            各ページのOCR結果リスト
        """

        # PDFの各ページサイズを取得
        import fitz
        page_dimensions = {}
        try:
            pdf_doc = fitz.open(pdf_path)
            for page_num in range(pdf_doc.page_count):
                page = pdf_doc[page_num]
                page_dimensions[page_num + 1] = {
                    'width': page.rect.width,
                    'height': page.rect.height
                }
                logger.info(
                    f"Page {page_num + 1} dimensions: "
                    f"{page.rect.width:.1f}x{page.rect.height:.1f}"
                )
            pdf_doc.close()
        except Exception as e:
            logger.warning(f"Failed to get page dimensions: {e}")

        # プロンプト構築
        prompt = self._build_ocr_prompt()

        # Gemini API呼び出し
        try:
            logger.info(f"Starting PDF OCR with {self.model}")

            # PDFファイルを読み込み
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            # Base64エンコード
            pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

            # Gemini API call for OCR (PDF直接送信)
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part(text=prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="application/pdf",
                            data=pdf_b64
                        )
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=1.0  # Gemini 3推奨値
                )
            )

            # 結果パース（ページサイズ情報を渡す）
            results = self._parse_multi_page_response(response.text, page_dimensions)
            logger.info(f"OCR completed for {len(results)} pages")

            return results

        except Exception as e:
            logger.error(
                f"Gemini PDF OCR failed: {str(e)}"
            )
            raise OCRException(
                "PDF OCR failed",
                details={"error": str(e)}
            )

    def _build_ocr_prompt(self) -> str:
        """OCR用プロンプト生成（改善版 - 図表検出精度向上）"""

        return """
あなたは高精度なPDF文書解析の専門家です。このPDFファイル全体から情報を抽出してください。

# 重要: 座標システムの理解
- PDFの座標は左上が原点(0,0)です
- x座標: 左から右へ増加（ピクセル単位）
- y座標: 上から下へ増加（ピクセル単位）
- すべての座標値は**実際のピクセル値**で記録してください（0-1の正規化値ではありません）

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

## 3. 図解・画像の高精度検出【重要改善】

### 3.1 検出対象
すべての図、表、写真、イラスト、グラフ、チャート、ダイアグラムを検出してください。

### 3.2 境界ボックス（Bounding Box）の正確な決定

**ステップ1: 全要素の識別**
図表を構成するすべての視覚要素を識別:
- ノード（円、四角、番号付きの記号）
- 矢印、線、接続線
- テキストラベル、番号、記号
- キャプション、タイトル、説明文
- 凡例、軸ラベル（グラフの場合）

**ステップ2: 最外縁の計算**
- 識別したすべての要素を包含する最小矩形を計算
- 特に重要：**最上部の要素のy座標を必ず含める**
- 最左端、最右端、最下部の要素も完全に含める

**ステップ3: 余白の追加**
- 計算した境界に10ピクセルの余白を追加
- これにより、切れ目のない完全な図表を確保

### 3.3 特殊な図表への対応

**アローダイアグラム・フローチャート:**
- すべての接続ノード（番号付き円など）を含める
- 最上段のノードから最下段のノードまで
- すべての矢印の端点を含む範囲

**表（テーブル）:**
- ヘッダー行を必ず含める
- すべてのセル境界を含める
- 表のキャプションも含める

**グラフ・チャート:**
- 軸ラベル、タイトル、凡例をすべて含める
- データポイントのラベルも含める

### 3.4 座標記録の形式
各図解について以下を正確に記録:
- **位置**: {"x": 左端x座標, "y": 最上端y座標, "width": 幅, "height": 高さ}
- **種類**: photo/illustration/diagram/table/graph
- **説明**: 図が何を示しているか
- **図内テキスト**: キャプション、ラベル等

## 4. レイアウト情報
- 段組み数（1段、2段、3段等）
- テキストと図解の配置関係
- 特殊なレイアウト要素（囲み記事、コラム、注釈ボックス等）

# 出力フォーマット

PDFの各ページについて、以下のJSON配列形式で出力してください:

```json
{
  "pages": [
    {
      "page_number": 1,
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
  ]
}
```

# クリティカルな注意事項

1. **座標精度の最優先**:
   - 図表の座標は**ピクセル単位で正確に**記録すること
   - 「おおよその座標」ではなく「正確な座標」を提供
   - 特にy座標の開始位置（最上部）に細心の注意を払う
   - 実際のPDFページサイズ（例: 842x595ピクセル）の座標系を使用

2. **完全性の確保**:
   - 図表のすべての構成要素を含む境界を設定
   - 部分的な切り取りは絶対に避ける
   - 疑わしい場合は、やや大きめの境界を設定

3. **複雑な図表の特別な扱い**:
   - アローダイアグラム、フローチャートなど複数要素から成る図表は、
     すべての要素（最上部のノードから最下部まで）を確実に含める
   - 例: ノード③⑥が上部、ノード①②⑤⑦⑧が下部にある場合、
     すべてを含む境界を設定

4. **自己検証**:
   - 各図表の境界を設定後、その境界内にすべての要素が
     含まれているか再確認すること

5. **読み順序とレイアウト**:
   - 書字方向を正しく判定し、読み順序を厳密に守る
   - 元のレイアウト構造（見出し階層、段落分け等）を維持

6. **全ページ処理**:
   PDFの全ページを処理し、pages配列に含めること
"""

    def _parse_multi_page_response(self, response_text: str, page_dimensions: dict = None) -> List[OCRResult]:
        """Gemini応答をパース（複数ページ対応）"""

        # JSONブロックを抽出
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)

        if not json_match:
            # JSONブロックが見つからない場合、全体をJSONとしてパース試行
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                raise ValueError("Failed to parse Gemini response: No valid JSON found")
        else:
            data = json.loads(json_match.group(1))

        # 各ページをパース
        results = []
        for page_data in data.get('pages', []):
            page_num = page_data.get('page_number', 1)
            # 該当ページのサイズを取得（存在しない場合はA4サイズをデフォルト）
            page_size = page_dimensions.get(page_num, {'width': 595, 'height': 842}) if page_dimensions else {'width': 595, 'height': 842}
            result = self._parse_page_data(page_data, page_size)
            results.append(result)

        return results

    def _parse_page_data(self, page_data: dict, page_size: dict = None) -> OCRResult:
        """1ページ分のデータをパース"""

        # FigureDataリストの構築
        figures = []
        for fig_data in page_data.get('figures', []):
            # 座標検証と調整（ページサイズ情報を渡す）
            validated_fig_data = self._validate_and_adjust_figure(fig_data, page_size)

            position = FigurePosition(**validated_fig_data['position'])
            figure = FigureData(
                id=validated_fig_data['id'],
                position=position,
                type=validated_fig_data['type'],
                description=validated_fig_data.get('description', ''),
                extracted_text=validated_fig_data.get('extracted_text')
            )
            figures.append(figure)

        # LayoutInfoの構築
        layout_data = page_data.get('layout_info', {})
        layout_info = LayoutInfo(
            primary_direction=layout_data.get('primary_direction', 'horizontal'),
            columns=layout_data.get('columns', 1),
            has_ruby=layout_data.get('has_ruby', False),
            special_elements=layout_data.get('special_elements', []),
            mixed_regions=layout_data.get('mixed_regions', [])
        )

        return OCRResult(
            page_number=page_data['page_number'],
            markdown_text=page_data['markdown_text'],
            figures=figures,
            layout_info=layout_info,
            detected_writing_mode=page_data['detected_writing_mode']
        )

    def _validate_and_adjust_figure(self, fig_data: dict, page_size: dict = None) -> dict:
        """
        図表座標の検証と調整

        Args:
            fig_data: 図表データ
            page_size: ページサイズ情報 {'width': xxx, 'height': xxx}

        Returns:
            検証・調整済みの図表データ
        """
        position = fig_data.get('position', {})
        x = position.get('x', 0)
        y = position.get('y', 0)
        width = position.get('width', 0)
        height = position.get('height', 0)
        fig_type = fig_data.get('type', '')
        description = fig_data.get('description', '')
        fig_id = fig_data.get('id', '')

        # ページサイズ取得（なければA4サイズをデフォルト）
        if page_size:
            page_width = page_size['width']
            page_height = page_size['height']
        else:
            page_width = 595  # A4縦
            page_height = 842

        # デバッグログ：Geminiから返された元の座標を記録
        logger.info(
            f"[Figure {fig_id}] Original coordinates from Gemini: "
            f"x={x}, y={y}, width={width}, height={height}, "
            f"page_size={page_width}x{page_height}, type={fig_type}"
        )

        # 座標の基本検証
        if width < 20 or height < 20:
            logger.warning(
                f"Suspiciously small figure detected: "
                f"type={fig_type}, size={width}x{height}, "
                f"description={description[:50]}"
            )

        # アローダイアグラム・フローチャートの特別処理（フォールバック戦略）
        if fig_type == 'diagram' or 'ダイアグラム' in description or 'arrow' in description.lower():
            # ダイアグラムは上部が切れやすいので、Geminiの検出精度に応じた対応

            # 【フォールバック戦略】
            # Geminiがy座標を極端に間違えている場合（y > 600 = ページの70%以上）
            # これは確実に誤検出なので、ページ上部から抽出する
            if y > 600:
                logger.warning(
                    f"[Figure {fig_id}] CRITICAL: Diagram detected at extreme bottom position (y={y}). "
                    f"This is likely a Gemini mis-detection. Applying FALLBACK strategy: "
                    f"Setting y=0 and using full upper page."
                )
                # ページ上半分全体を対象にする（y=0から元の高さ + 元のy座標まで）
                adjusted_y = 0
                # 元の図の下端を維持しつつ、上部を0から開始
                adjusted_height = min(y + height + 50, page_height)  # 下に50px余裕追加

                logger.info(
                    f"[Figure {fig_id}] FALLBACK adjustment: "
                    f"y {y} -> {adjusted_y}, height {height} -> {adjusted_height}"
                )

                fig_data['position']['y'] = adjusted_y
                fig_data['position']['height'] = adjusted_height
                y = adjusted_y
                height = adjusted_height

            # ページ中央付近の図（y座標が400-600）- 上部が切れている可能性大
            elif y > 400:
                # より積極的な拡張：元のy座標の70%を上方拡張
                expansion = int(y * 0.7)  # y=450なら315px上方拡張
                adjusted_y = max(0, y - expansion)
                adjusted_height = height + (y - adjusted_y) + 100  # さらに下に100px余裕追加

                logger.warning(
                    f"[Figure {fig_id}] Diagram starts mid-page (y={y}), likely missing top nodes. "
                    f"Applying AGGRESSIVE expansion: {expansion}px upward"
                )
                logger.info(
                    f"[Figure {fig_id}] Mid-page diagram adjustment: "
                    f"y {y} -> {adjusted_y}, height {height} -> {adjusted_height}, "
                    f"expansion={expansion}px"
                )

                fig_data['position']['y'] = adjusted_y
                fig_data['position']['height'] = adjusted_height
                y = adjusted_y
                height = adjusted_height

            # 高さが不十分な場合
            elif height < 400:
                expansion = max(200, 400 - height)
                adjusted_y = max(0, y - expansion)
                adjusted_height = height + (y - adjusted_y) + 100  # 下にも余裕追加

                logger.info(
                    f"[Figure {fig_id}] Small diagram detected (height={height}). "
                    f"Expanding: y {y} -> {adjusted_y}, height {height} -> {adjusted_height}"
                )

                fig_data['position']['y'] = adjusted_y
                fig_data['position']['height'] = adjusted_height
                y = adjusted_y
                height = adjusted_height

        # 表（table）の特別処理
        if fig_type == 'table' and y > 350:
            # 表も上部（ヘッダー行）が切れやすいので、上方向に拡張
            table_expansion = 50  # 表の場合は控えめに50ピクセル拡張

            adjusted_y = max(0, y - table_expansion)
            adjusted_height = height + (y - adjusted_y)

            logger.info(
                f"[Figure {fig_id}] Adjusting table bounding box: "
                f"y {y} -> {adjusted_y}, height {height} -> {adjusted_height}"
            )

            fig_data['position']['y'] = adjusted_y
            fig_data['position']['height'] = adjusted_height

            # 調整後の値を更新
            y = adjusted_y
            height = adjusted_height

        # アスペクト比の検証
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if aspect_ratio > 20 or aspect_ratio < 0.05:
                logger.warning(
                    f"Unusual aspect ratio detected: {aspect_ratio:.2f} "
                    f"for {fig_type} ({width}x{height})"
                )

        # Geminiが返す座標がページサイズを超える場合の調整
        # Geminiは時々間違った座標（特にx2, y2）を返すことがある

        # x座標とwidthの調整
        if x + width > page_width:
            # 右端がページ幅を超える場合
            original_width = width

            # ケース1: x座標は正しいが幅が大きすぎる（Geminiがx2を間違えた）
            if x < page_width * 0.9:  # x座標がページの90%以内なら有効と判断
                # 幅をページ内に収める（int型に変換）
                adjusted_width = int(page_width - x - 10)  # 10ピクセルの余白
                logger.warning(
                    f"[Figure {fig_id}] Width exceeds page bounds - adjusting: "
                    f"width {original_width} -> {adjusted_width} "
                    f"(x={x}, x+width={x+original_width}, page_width={page_width})"
                )
                width = adjusted_width
            else:
                # ケース2: x座標自体が無効
                logger.warning(f"[Figure {fig_id}] X coordinate exceeds page bounds: {x} -> 0")
                x = 0
                width = int(min(original_width, page_width - 20))  # ページ幅から余白を引いた値（int型）

        # y座標とheightの調整
        if y + height > page_height:
            # 下端がページ高さを超える場合
            original_height = height

            if y < page_height * 0.9:  # y座標がページの90%以内なら有効と判断
                # 高さをページ内に収める（int型に変換）
                adjusted_height = int(page_height - y - 10)  # 10ピクセルの余白
                logger.warning(
                    f"[Figure {fig_id}] Height exceeds page bounds - adjusting: "
                    f"height {original_height} -> {adjusted_height} "
                    f"(y={y}, y+height={y+original_height}, page_height={page_height})"
                )
                height = adjusted_height
            else:
                # y座標自体が無効
                logger.warning(f"[Figure {fig_id}] Y coordinate exceeds page bounds: {y} -> 0")
                y = 0
                height = int(min(original_height, page_height - 20))  # int型に変換

        # 座標が負の値でないことを確認し、int型に変換
        fig_data['position']['x'] = int(max(0, x))
        fig_data['position']['y'] = int(max(0, fig_data['position'].get('y', y)))  # 調整済みの値を使用
        fig_data['position']['width'] = int(max(1, width))
        fig_data['position']['height'] = int(max(1, fig_data['position'].get('height', height)))  # 調整済みの値を使用

        # 最終的な座標をログ出力（変更があった場合）
        final_x = fig_data['position']['x']
        final_y = fig_data['position']['y']
        final_width = fig_data['position']['width']
        final_height = fig_data['position']['height']

        if (final_x != position.get('x', 0) or final_y != position.get('y', 0) or
                final_width != position.get('width', 0) or final_height != position.get('height', 0)):
            logger.info(
                f"[Figure {fig_id}] Final adjusted coordinates: "
                f"x={final_x}, y={final_y}, width={final_width}, height={final_height}"
            )

        return fig_data
