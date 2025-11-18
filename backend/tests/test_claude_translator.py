"""
Claude翻訳サービスのテスト
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.claude_translator import ClaudeTranslator


@pytest.mark.unit
@pytest.mark.asyncio
class TestClaudeTranslator:
    """Claude翻訳サービスのテスト"""

    @pytest.fixture
    def api_key(self):
        """テスト用APIキー"""
        return "test_claude_api_key"

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
    def mock_claude_response(self):
        """モックClaude API応答"""
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = """# Chapter 1 Introduction

This is a sample textbook text.

## 1.1 Overview

Please refer to Figure 1.

![Figure 1](figures/fig1.png)
"""
        mock_response.content = [mock_content]
        return mock_response

    @patch('app.services.claude_translator.AsyncAnthropic')
    def test_init(self, mock_anthropic, api_key):
        """初期化テスト"""
        translator = ClaudeTranslator(api_key)

        mock_anthropic.assert_called_once_with(api_key=api_key)
        assert translator.model == "claude-sonnet-4-5-20250929"

    @patch('app.services.claude_translator.AsyncAnthropic')
    async def test_translate_success(
        self,
        mock_anthropic,
        api_key,
        source_text,
        mock_claude_response
    ):
        """translate - 成功ケース"""
        # モッククライアントの設定
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
        mock_anthropic.return_value = mock_client

        translator = ClaudeTranslator(api_key)
        result = await translator.translate(source_text, target_language="en")

        # 結果検証
        assert "Chapter 1" in result
        assert "Introduction" in result
        assert "Figure 1" in result
        assert "![Figure 1](figures/fig1.png)" in result

        # API呼び出しの検証
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_args.kwargs["max_tokens"] == 8000
        assert call_args.kwargs["timeout"] == 120.0

    @patch('app.services.claude_translator.AsyncAnthropic')
    async def test_translate_multiple_languages(
        self,
        mock_anthropic,
        api_key,
        source_text
    ):
        """translate - 複数言語対応"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Translated text"
        mock_response.content = [mock_content]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        translator = ClaudeTranslator(api_key)

        # 各言語でテスト
        languages = ["en", "zh", "zh-TW", "ko", "vi", "th", "es", "fr"]
        for lang in languages:
            result = await translator.translate(source_text, target_language=lang)
            assert result == "Translated text"

    @patch('app.services.claude_translator.AsyncAnthropic')
    async def test_translate_with_context(
        self,
        mock_anthropic,
        api_key,
        source_text,
        mock_claude_response
    ):
        """translate - コンテキスト付き翻訳"""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
        mock_anthropic.return_value = mock_client

        translator = ClaudeTranslator(api_key)
        context = {"subject": "mathematics", "grade": "high_school"}

        result = await translator.translate(
            source_text,
            target_language="en",
            context=context
        )

        assert "Chapter 1" in result

    @patch('app.services.claude_translator.AsyncAnthropic')
    async def test_translate_api_error(
        self,
        mock_anthropic,
        api_key,
        source_text
    ):
        """translate - API呼び出しエラー"""
        # モッククライアントがエラーを返すように設定
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API connection error")
        )
        mock_anthropic.return_value = mock_client

        translator = ClaudeTranslator(api_key)

        with pytest.raises(Exception, match="Claude translation failed"):
            await translator.translate(source_text, target_language="en")

    @patch('app.services.claude_translator.AsyncAnthropic')
    async def test_translate_empty_text(
        self,
        mock_anthropic,
        api_key,
        mock_claude_response
    ):
        """translate - 空のテキスト"""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response)
        mock_anthropic.return_value = mock_client

        translator = ClaudeTranslator(api_key)
        result = await translator.translate("", target_language="en")

        # 空のテキストでも処理が完了すること
        assert isinstance(result, str)

    def test_language_names_mapping(self, api_key):
        """LANGUAGE_NAMES マッピングの検証"""
        translator = ClaudeTranslator(api_key)

        expected_mappings = {
            'en': 'English',
            'zh': '简体中文 (Simplified Chinese)',
            'zh-TW': '繁體中文 (Traditional Chinese)',
            'ko': '한국어 (Korean)',
            'vi': 'Tiếng Việt (Vietnamese)',
            'th': 'ไทย (Thai)',
            'es': 'Español (Spanish)',
            'fr': 'Français (French)'
        }

        for lang_code, lang_name in expected_mappings.items():
            assert translator.LANGUAGE_NAMES[lang_code] == lang_name
