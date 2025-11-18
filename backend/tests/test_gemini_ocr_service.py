"""
Gemini OCRサービスのテスト
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from PIL import Image

from app.services.gemini_ocr_service import GeminiOCRService
from app.models.schemas import OCRResult, FigurePosition
from app.exceptions import OCRException


@pytest.mark.unit
class TestGeminiOCRService:
    """Gemini OCRサービスのテスト"""

    @pytest.fixture
    def api_key(self):
        """テスト用APIキー"""
        return "test_gemini_api_key"

    @pytest.fixture
    def sample_image_bytes(self):
        """テスト用画像データ"""
        # 小さな白い画像を生成
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    @pytest.fixture
    def mock_gemini_response(self):
        """モックGemini API応答"""
        json_response = """{
  "detected_writing_mode": "horizontal",
  "markdown_text": "# 第1章\\n\\nテスト内容です。",
  "figures": [
    {
      "id": 1,
      "position": {"x": 100, "y": 200, "width": 400, "height": 300},
      "type": "photo",
      "description": "テスト画像",
      "extracted_text": "図1"
    }
  ],
  "layout_info": {
    "primary_direction": "horizontal",
    "columns": 1,
    "has_ruby": false,
    "special_elements": [],
    "mixed_regions": []
  }
}"""
        return f"```json\n{json_response}\n```"

    @patch('app.services.gemini_ocr_service.genai')
    def test_init(self, mock_genai, api_key):
        """初期化テスト"""
        GeminiOCRService(api_key)

        mock_genai.configure.assert_called_once_with(api_key=api_key)
        mock_genai.GenerativeModel.assert_called_once_with('gemini-2.0-flash-exp')

    @pytest.mark.asyncio
    @patch('app.services.gemini_ocr_service.genai')
    async def test_extract_page_success(
        self,
        mock_genai,
        api_key,
        sample_image_bytes,
        mock_gemini_response
    ):
        """extract_page - 成功ケース"""
        # モックモデルの設定
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_gemini_response
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        service = GeminiOCRService(api_key)
        result = await service.extract_page(sample_image_bytes, page_number=1)

        # 結果検証
        assert isinstance(result, OCRResult)
        assert result.page_number == 1
        assert result.detected_writing_mode == "horizontal"
        assert "第1章" in result.markdown_text
        assert len(result.figures) == 1
        assert result.figures[0].type == "photo"
        assert result.layout_info.primary_direction == "horizontal"

    @pytest.mark.asyncio
    @patch('app.services.gemini_ocr_service.genai')
    async def test_extract_page_api_error(
        self,
        mock_genai,
        api_key,
        sample_image_bytes
    ):
        """extract_page - API呼び出しエラー"""
        # モックモデルがエラーを返すように設定
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("API connection error")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        service = GeminiOCRService(api_key)

        with pytest.raises(OCRException) as exc_info:
            await service.extract_page(sample_image_bytes, page_number=5)

        assert "OCR failed for page 5" in str(exc_info.value)
        assert exc_info.value.details["page"] == 5

    def test_parse_response_with_json_block(self, api_key, mock_gemini_response):
        """_parse_response - JSONブロック形式"""
        service = GeminiOCRService(api_key)
        result = service._parse_response(mock_gemini_response, page_number=2)

        assert result.page_number == 2
        assert result.detected_writing_mode == "horizontal"
        assert len(result.figures) == 1
        assert result.figures[0].position.x == 100
        assert result.figures[0].position.y == 200

    def test_parse_response_plain_json(self, api_key):
        """_parse_response - プレーンJSON形式"""
        plain_json = """{
  "detected_writing_mode": "vertical",
  "markdown_text": "# 縦書きテスト",
  "figures": [],
  "layout_info": {
    "primary_direction": "vertical",
    "columns": 2,
    "has_ruby": true,
    "special_elements": ["注釈"],
    "mixed_regions": []
  }
}"""
        service = GeminiOCRService(api_key)
        result = service._parse_response(plain_json, page_number=3)

        assert result.page_number == 3
        assert result.detected_writing_mode == "vertical"
        assert len(result.figures) == 0
        assert result.layout_info.columns == 2
        assert result.layout_info.has_ruby is True

    def test_parse_response_invalid_json(self, api_key):
        """_parse_response - 不正なJSON"""
        invalid_response = "This is not JSON at all"

        service = GeminiOCRService(api_key)

        with pytest.raises(ValueError, match="No valid JSON found"):
            service._parse_response(invalid_response, page_number=1)

    @pytest.mark.asyncio
    async def test_extract_figures_from_image(self, api_key):
        """extract_figures_from_image - 図解切り取り"""
        # テスト用の大きな画像を作成
        img = Image.new('RGB', (800, 600), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        # 切り取り位置を定義
        figure_positions = [
            FigurePosition(x=100, y=100, width=200, height=150),
            FigurePosition(x=400, y=200, width=300, height=250)
        ]

        service = GeminiOCRService(api_key)
        cropped_figures = await service.extract_figures_from_image(
            image_bytes,
            figure_positions
        )

        # 結果検証
        assert len(cropped_figures) == 2
        assert all(isinstance(fig, bytes) for fig in cropped_figures)

        # 最初の切り取り画像のサイズ確認
        cropped_img1 = Image.open(BytesIO(cropped_figures[0]))
        assert cropped_img1.size == (200, 150)

        # 2番目の切り取り画像のサイズ確認
        cropped_img2 = Image.open(BytesIO(cropped_figures[1]))
        assert cropped_img2.size == (300, 250)

    def test_build_ocr_prompt(self, api_key):
        """_build_ocr_prompt - プロンプト生成"""
        service = GeminiOCRService(api_key)
        prompt = service._build_ocr_prompt()

        # プロンプト内容の検証
        assert "書字方向" in prompt
        assert "vertical" in prompt
        assert "horizontal" in prompt
        assert "JSON" in prompt
        assert "detected_writing_mode" in prompt
