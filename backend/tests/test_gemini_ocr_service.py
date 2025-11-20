"""
Gemini OCRサービスのテスト (PDF直接送信版)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import tempfile
import os

from app.services.gemini_ocr_service import GeminiOCRService
from app.models.schemas import OCRResult
from app.exceptions import OCRException


@pytest.mark.unit
class TestGeminiOCRService:
    """Gemini OCRサービスのテスト"""

    @pytest.fixture
    def api_key(self):
        """テスト用APIキー"""
        return "test_gemini_api_key"

    @pytest.fixture
    def mock_multi_page_response(self):
        """モックGemini API応答 (複数ページ)"""
        json_response = """{
  "pages": [
    {
      "page_number": 1,
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
    },
    {
      "page_number": 2,
      "detected_writing_mode": "vertical",
      "markdown_text": "# 第2章\\n\\n縦書きテスト。",
      "figures": [],
      "layout_info": {
        "primary_direction": "vertical",
        "columns": 2,
        "has_ruby": true,
        "special_elements": ["注釈"],
        "mixed_regions": []
      }
    }
  ]
}"""
        return f"```json\n{json_response}\n```"

    @patch('app.services.gemini_ocr_service.genai.Client')
    def test_init(self, mock_client_class, api_key):
        """初期化テスト"""
        GeminiOCRService(api_key)
        mock_client_class.assert_called_once_with(api_key=api_key)

    @pytest.mark.asyncio
    @patch('app.services.gemini_ocr_service.genai.Client')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_pdf_content')
    async def test_extract_from_pdf_success(
        self,
        mock_file,
        mock_client_class,
        api_key,
        mock_multi_page_response
    ):
        """extract_from_pdf - 成功ケース"""
        # モッククライアントとレスポンスの設定
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_multi_page_response

        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        service = GeminiOCRService(api_key)

        # 一時PDFファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'fake_pdf_content')
            pdf_path = tmp_pdf.name

        try:
            results = await service.extract_from_pdf(pdf_path)

            # 結果検証
            assert isinstance(results, list)
            assert len(results) == 2

            # ページ1の検証
            assert isinstance(results[0], OCRResult)
            assert results[0].page_number == 1
            assert results[0].detected_writing_mode == "horizontal"
            assert "第1章" in results[0].markdown_text
            assert len(results[0].figures) == 1
            assert results[0].figures[0].type == "photo"
            assert results[0].layout_info.primary_direction == "horizontal"

            # ページ2の検証
            assert results[1].page_number == 2
            assert results[1].detected_writing_mode == "vertical"
            assert "第2章" in results[1].markdown_text
            assert len(results[1].figures) == 0
            assert results[1].layout_info.columns == 2
            assert results[1].layout_info.has_ruby is True
        finally:
            # 一時ファイルを削除
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

    @pytest.mark.asyncio
    @patch('app.services.gemini_ocr_service.genai.Client')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_pdf_content')
    async def test_extract_from_pdf_api_error(
        self,
        mock_file,
        mock_client_class,
        api_key
    ):
        """extract_from_pdf - API呼び出しエラー"""
        # モッククライアントがエラーを返すように設定
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content = AsyncMock(
            side_effect=Exception("API connection error")
        )
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        service = GeminiOCRService(api_key)

        # 一時PDFファイルを作成
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(b'fake_pdf_content')
            pdf_path = tmp_pdf.name

        try:
            with pytest.raises(OCRException) as exc_info:
                await service.extract_from_pdf(pdf_path)

            assert "PDF OCR failed" in str(exc_info.value)
        finally:
            # 一時ファイルを削除
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

    def test_parse_multi_page_response_with_json_block(self, api_key, mock_multi_page_response):
        """_parse_multi_page_response - JSONブロック形式"""
        service = GeminiOCRService(api_key)
        results = service._parse_multi_page_response(mock_multi_page_response)

        assert len(results) == 2
        assert results[0].page_number == 1
        assert results[1].page_number == 2
        assert results[0].detected_writing_mode == "horizontal"
        assert results[1].detected_writing_mode == "vertical"

    def test_parse_multi_page_response_plain_json(self, api_key):
        """_parse_multi_page_response - プレーンJSON形式"""
        plain_json = """{
  "pages": [
    {
      "page_number": 1,
      "detected_writing_mode": "horizontal",
      "markdown_text": "# テスト",
      "figures": [],
      "layout_info": {
        "primary_direction": "horizontal",
        "columns": 1,
        "has_ruby": false,
        "special_elements": [],
        "mixed_regions": []
      }
    }
  ]
}"""
        service = GeminiOCRService(api_key)
        results = service._parse_multi_page_response(plain_json)

        assert len(results) == 1
        assert results[0].page_number == 1
        assert results[0].detected_writing_mode == "horizontal"

    def test_parse_multi_page_response_invalid_json(self, api_key):
        """_parse_multi_page_response - 不正なJSON"""
        invalid_response = "This is not JSON at all"

        service = GeminiOCRService(api_key)

        with pytest.raises(ValueError, match="No valid JSON found"):
            service._parse_multi_page_response(invalid_response)

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
        assert "pages" in prompt
