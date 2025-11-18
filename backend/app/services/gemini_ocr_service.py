"""
Gemini OCRサービス
"""
import google.generativeai as genai
from typing import List
import json
import re
from PIL import Image
import io
import logging

from app.models.schemas import OCRResult, FigureData, LayoutInfo, FigurePosition
from app.utils.retry import async_retry
from app.exceptions import OCRException, APIRateLimitException

logger = logging.getLogger(__name__)


class GeminiOCRService:
    """Gemini 2.5 ProによるOCRサービス"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    @async_retry(
        max_retries=3,
        base_delay=2.0,
        max_delay=60.0,
        exceptions=(Exception,),
        rate_limit_exceptions=(APIRateLimitException,)
    )
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

        # Gemini API呼び出し
        try:
            logger.info(f"Starting OCR for page {page_number}")

            # 画像を PIL Image として準備
            image = Image.open(io.BytesIO(image_bytes))

            response = await self.model.generate_content_async([
                prompt,
                image
            ])

            # 結果パース
            result = self._parse_response(response.text, page_number)
            logger.info(f"OCR completed for page {page_number}")
            return result

        except Exception as e:
            logger.error(
                f"Gemini OCR failed for page {page_number}: {str(e)}"
            )
            raise OCRException(
                f"OCR failed for page {page_number}",
                details={"page": page_number, "error": str(e)}
            )

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

        # FigureDataリストの構築
        figures = []
        for fig_data in data.get('figures', []):
            position = FigurePosition(**fig_data['position'])
            figure = FigureData(
                id=fig_data['id'],
                position=position,
                type=fig_data['type'],
                description=fig_data.get('description', ''),
                extracted_text=fig_data.get('extracted_text')
            )
            figures.append(figure)

        # LayoutInfoの構築
        layout_data = data.get('layout_info', {})
        layout_info = LayoutInfo(
            primary_direction=layout_data.get('primary_direction', 'horizontal'),
            columns=layout_data.get('columns', 1),
            has_ruby=layout_data.get('has_ruby', False),
            special_elements=layout_data.get('special_elements', []),
            mixed_regions=layout_data.get('mixed_regions', [])
        )

        return OCRResult(
            page_number=page_number,
            markdown_text=data['markdown_text'],
            figures=figures,
            layout_info=layout_info,
            detected_writing_mode=data['detected_writing_mode']
        )

    async def extract_figures_from_image(
        self,
        image_bytes: bytes,
        figure_positions: List[FigurePosition]
    ) -> List[bytes]:
        """
        図解を画像から切り取り

        Args:
            image_bytes: ページ全体の画像
            figure_positions: 図解の位置情報リスト

        Returns:
            切り取られた図解画像のリスト
        """
        # 画像を開く
        img = Image.open(io.BytesIO(image_bytes))

        cropped_figures = []

        for fig_pos in figure_positions:
            # 切り取り
            cropped = img.crop((
                fig_pos.x,
                fig_pos.y,
                fig_pos.x + fig_pos.width,
                fig_pos.y + fig_pos.height
            ))

            # バイト列化
            cropped_bytes = io.BytesIO()
            cropped.save(cropped_bytes, format='PNG')
            cropped_figures.append(cropped_bytes.getvalue())

        return cropped_figures
