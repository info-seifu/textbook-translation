"""
翻訳オーケストレーター
翻訳処理全体の管理
"""
from app.services.claude_translator import ClaudeTranslator
from app.services.gemini_translator import GeminiTranslator
from typing import Literal
import httpx


TranslatorEngine = Literal['claude', 'gemini']


class TranslationOrchestrator:
    """翻訳処理の管理"""

    def __init__(
        self,
        claude_api_key: str,
        gemini_api_key: str,
        supabase_client
    ):
        self.claude = ClaudeTranslator(claude_api_key)
        self.gemini = GeminiTranslator(gemini_api_key)
        self.db_client = supabase_client

    async def translate_document(
        self,
        job_id: str,
        target_language: str,
        translator_engine: TranslatorEngine = 'claude'
    ) -> str:
        """
        文書全体を翻訳

        Args:
            job_id: 翻訳ジョブID
            target_language: 翻訳先言語
            translator_engine: 使用する翻訳エンジン

        Returns:
            翻訳済みマークダウンのURL
        """

        # 1. マスターマークダウンを取得
        job = self.db_client.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise Exception(f"Job {job_id} not found")

        master_md_url = job.data['japanese_markdown_url']

        if not master_md_url:
            raise Exception(f"Master markdown not found for job {job_id}")

        # マスターマークダウンをダウンロード
        master_text = await self._download_text(master_md_url)

        # 2. 翻訳エンジン選択
        translator = self.claude if translator_engine == 'claude' else self.gemini

        # 3. 翻訳実行
        translated_text = await translator.translate(
            master_text,
            target_language,
            context=job.data.get('layout_metadata')
        )

        # 4. 翻訳結果を保存
        translated_url = await self._save_translation(
            job_id,
            target_language,
            translated_text
        )

        return translated_url

    async def _download_text(self, url: str) -> str:
        """StorageからテキストダウンロードまたはURLから直接取得"""

        try:
            # ローカルファイルの場合
            if url.startswith('file://'):
                file_path = url.replace('file://', '')
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            # HTTPの場合
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            raise Exception(f"Failed to download text from {url}: {str(e)}")

    async def _save_translation(
        self,
        job_id: str,
        language: str,
        text: str
    ) -> str:
        """翻訳をStorageに保存"""

        file_path = f"{job_id}/translated_{language}.md"

        try:
            # アップロード
            self.db_client.storage.from_('documents').upload(
                file_path,
                text.encode('utf-8'),
                {'content-type': 'text/markdown'}
            )

            # 公開URLを取得
            url = self.db_client.storage.from_('documents').get_public_url(file_path)
            return url

        except Exception as e:
            raise Exception(f"Failed to save translation: {str(e)}")
