"""
Gemini翻訳サービス
"""
import google.generativeai as genai
from typing import Optional
from app.services.translator_base import TranslatorBase
from app.utils.retry_helper import with_retry
import logging

logger = logging.getLogger(__name__)


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
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    @with_retry(max_retries=3, initial_delay=2.0)
    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: Optional[dict] = None
    ) -> str:
        """Gemini Flashで翻訳（リトライ機能付き）"""

        target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

        logger.info(f"Starting translation to {target_language} using Gemini Flash")

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

        try:
            response = await self.model.generate_content_async(prompt)
            translated_text = response.text
            logger.info(f"Translation completed successfully. Output length: {len(translated_text)} chars")
            return translated_text

        except Exception as e:
            logger.error(f"Gemini translation failed: {str(e)}")
            raise Exception(f"Gemini translation failed: {str(e)}")
