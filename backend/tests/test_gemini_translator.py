"""
Gemini翻訳サービスのテスト
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.gemini_translator import GeminiTranslator


@pytest.mark.unit
@pytest.mark.asyncio
class TestGeminiTranslator:
    """Gemini翻訳サービスのテスト"""

    @pytest.fixture
    def api_key(self):
        """テスト用APIキー"""
        return "test_gemini_api_key"

    @pytest.fixture
    def source_text(self):
        """翻訳元テキスト"""
        return """# 第1章 はじめに

これは教科書のサンプルテキストです。

## 1.1 概要

図1を参照してください。

![図1](figures/fig1.png)
"""

    @pytest.fixture
    def translated_text(self):
        """翻訳後テキスト"""
        return """# Chapter 1 Introduction

This is a sample textbook text.

## 1.1 Overview

Please refer to Figure 1.

![Figure 1](figures/fig1.png)
"""

    @patch('app.services.gemini_translator.genai.Client')
    def test_init(self, mock_client_class, api_key):
        """初期化テスト"""
        GeminiTranslator(api_key)

        mock_client_class.assert_called_once_with(api_key=api_key)

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_success(
        self,
        mock_client_class,
        api_key,
        source_text,
        translated_text
    ):
        """translate - 成功ケース"""
        # モッククライアントとレスポンスの設定
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = translated_text

        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        translator = GeminiTranslator(api_key)
        result = await translator.translate(source_text, target_language="en")

        # 結果検証
        assert "Chapter 1" in result
        assert "Introduction" in result
        assert "Figure 1" in result
        assert "![Figure 1](figures/fig1.png)" in result

        # API呼び出しの検証
        mock_models.generate_content.assert_called_once()

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_multiple_languages(
        self,
        mock_client_class,
        api_key,
        source_text
    ):
        """translate - 複数言語対応"""
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Translated text"
        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        translator = GeminiTranslator(api_key)

        # 各言語でテスト
        languages = ["en", "zh", "zh-TW", "ko", "vi", "th", "es", "fr"]
        for lang in languages:
            result = await translator.translate(source_text, target_language=lang)
            assert result == "Translated text"

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_with_context(
        self,
        mock_client_class,
        api_key,
        source_text,
        translated_text
    ):
        """translate - コンテキスト付き翻訳"""
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = translated_text
        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        translator = GeminiTranslator(api_key)
        context = {"subject": "science", "grade": "middle_school"}

        result = await translator.translate(
            source_text,
            target_language="en",
            context=context
        )

        assert "Chapter 1" in result

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_api_error(
        self,
        mock_client_class,
        api_key,
        source_text
    ):
        """translate - API呼び出しエラー"""
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

        translator = GeminiTranslator(api_key)

        with pytest.raises(Exception, match="Gemini translation failed"):
            await translator.translate(source_text, target_language="en")

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_empty_text(
        self,
        mock_client_class,
        api_key
    ):
        """translate - 空のテキスト"""
        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        translator = GeminiTranslator(api_key)
        result = await translator.translate("", target_language="en")

        # 空のテキストでも処理が完了すること
        assert isinstance(result, str)

    def test_language_names_mapping(self, api_key):
        """LANGUAGE_NAMES マッピングの検証"""
        translator = GeminiTranslator(api_key)

        expected_mappings = {
            'en': 'English',
            'zh': 'Simplified Chinese (简体中文)',
            'zh-TW': 'Traditional Chinese (繁體中文)',
            'ko': 'Korean (한국어)',
            'vi': 'Vietnamese (Tiếng Việt)',
            'th': 'Thai (ไทย)',
            'es': 'Spanish (Español)',
            'fr': 'French (Français)'
        }

        for lang_code, lang_name in expected_mappings.items():
            assert translator.LANGUAGE_NAMES[lang_code] == lang_name

    @patch('app.services.gemini_translator.genai.Client')
    async def test_translate_preserves_markdown_structure(
        self,
        mock_client_class,
        api_key
    ):
        """translate - Markdown構造の保持"""
        source = """# 見出し1
## 見出し2
- リスト項目1
- リスト項目2

**太字**と*斜体*のテスト。
"""
        translated = """# Heading 1
## Heading 2
- List item 1
- List item 2

**Bold** and *italic* test.
"""

        mock_client = MagicMock()
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_response = MagicMock()
        mock_response.text = translated
        mock_models.generate_content = AsyncMock(return_value=mock_response)
        mock_aio.models = mock_models
        mock_client.aio = mock_aio
        mock_client_class.return_value = mock_client

        translator = GeminiTranslator(api_key)
        result = await translator.translate(source, target_language="en")

        # Markdown構造が保持されていることを確認
        assert "# Heading 1" in result
        assert "## Heading 2" in result
        assert "- List item" in result
        assert "**Bold**" in result
        assert "*italic*" in result
