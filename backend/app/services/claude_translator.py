"""
Claude翻訳サービス
"""
from anthropic import AsyncAnthropic
from typing import Optional
from app.services.translator_base import TranslatorBase
from app.utils.retry import async_retry
from app.exceptions import APIRateLimitException
import logging

logger = logging.getLogger(__name__)


class ClaudeTranslator(TranslatorBase):
    """Claude Sonnetによる翻訳"""

    LANGUAGE_NAMES = {
        'en': 'English',
        'zh': '简体中文 (Simplified Chinese)',
        'zh-TW': '繁體中文 (Traditional Chinese)',
        'ko': '한국어 (Korean)',
        'vi': 'Tiếng Việt (Vietnamese)',
        'th': 'ไทย (Thai)',
        'es': 'Español (Spanish)',
        'fr': 'Français (French)'
    }

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    @async_retry(
        max_retries=3,
        base_delay=2.0,
        max_delay=60.0,
        exceptions=(Exception,),
        rate_limit_exceptions=(APIRateLimitException,)
    )
    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: Optional[dict] = None
    ) -> str:
        """Claude Sonnetで翻訳（リトライ機能付き）"""

        target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

        logger.info(f"Starting translation to {target_language} using Claude Sonnet")

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

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                timeout=120.0  # 2分のタイムアウト
            )

            translated_text = response.content[0].text
            logger.info(f"Translation completed successfully. Output length: {len(translated_text)} chars")
            return translated_text

        except Exception as e:
            logger.error(f"Claude translation failed: {str(e)}")
            raise Exception(f"Claude translation failed: {str(e)}")
