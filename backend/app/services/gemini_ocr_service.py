"""
Gemini OCRサービス (PDF直接送信版)
"""
from google import genai
from google.genai import types
from typing import List
import json
import re
from pathlib import Path
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

            # 結果パース
            results = self._parse_multi_page_response(response.text)
            logger.info(f"OCR completed for {len(results)} pages")

            return results

        except Exception as e:
            logger.error(
                f"Gemini PDF OCR failed: {str(e)}"
            )
            raise OCRException(
                f"PDF OCR failed",
                details={"error": str(e)}
            )

    def _build_ocr_prompt(self) -> str:
        """OCR用プロンプト生成"""

        return """
あなたは日本語教科書のOCR専門家です。このPDFファイル全体から情報を抽出してください。

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

# 重要な注意事項

1. **読み順序の正確性**: 書字方向を正しく判定し、その方向に従って読み順序を厳密に守ること
2. **図解の位置精度**: 図解の位置を可能な限り正確に記録すること
3. **ルビ・特殊記号**: ルビ、縦中横、特殊記号も正確に抽出すること
4. **レイアウトの忠実性**: 元のレイアウト構造（見出し階層、段落分け等）を維持すること
5. **全ページ処理**: PDFの全ページを処理し、pages配列に含めること
"""

    def _parse_multi_page_response(self, response_text: str) -> List[OCRResult]:
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
            result = self._parse_page_data(page_data)
            results.append(result)

        return results

    def _parse_page_data(self, page_data: dict) -> OCRResult:
        """1ページ分のデータをパース"""

        # FigureDataリストの構築
        figures = []
        for fig_data in page_data.get('figures', []):
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

    @async_retry(
        max_retries=2,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(Exception,),
        rate_limit_exceptions=(APIRateLimitException,)
    )
    async def verify_figure_image(self, image_path: str) -> dict:
        """
        抽出された画像が実際に図表かどうかをGeminiで検証

        Args:
            image_path: 検証する画像のパス

        Returns:
            {
                "is_figure": bool,  # 図表かどうか
                "type": str or None,  # 図表の種類 (table, diagram, graph, illustrationなど)
                "confidence": float,  # 信頼度 (0.0-1.0)
                "reason": str  # 判断理由
            }
        """
        prompt = """この画像を見て、以下の質問に答えてください:

1. これは図表（グラフ、表、ダイアグラム、フローチャート、イラストなど）ですか？
2. もし図表であれば、どのタイプですか？

回答は以下のJSON形式のみで返してください（説明文は不要）:
{
  "is_figure": true/false,
  "type": "table" / "diagram" / "graph" / "illustration" / "photo" / null,
  "confidence": 0.0-1.0,
  "reason": "判断理由（1文で簡潔に）"
}

注意:
- 通常のテキスト、選択肢、問題文、空白ページなどは図表ではありません
- 表やグラフ、ダイアグラムなど明確な図表要素がある場合のみis_figure=trueとしてください
"""

        try:
            # 画像を読み込んでbase64エンコード
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Gemini APIに送信
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part(text=prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=image_data
                        )
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            # レスポンスをパース
            result_text = response.text.strip()

            # JSONパース
            result = json.loads(result_text)

            logger.debug(f"Figure verification result for {image_path}: {result}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Gemini verification response: {e}")
            # パースに失敗した場合はデフォルト値を返す
            return {
                "is_figure": False,
                "type": None,
                "confidence": 0.0,
                "reason": "Failed to parse response"
            }
        except Exception as e:
            logger.error(f"Error verifying figure image {image_path}: {e}")
            raise
