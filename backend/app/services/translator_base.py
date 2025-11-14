"""
翻訳エンジンの基底クラス
"""
from abc import ABC, abstractmethod
from typing import Optional


class TranslatorBase(ABC):
    """翻訳エンジンの基底クラス"""

    @abstractmethod
    async def translate(
        self,
        source_text: str,
        target_language: str,
        context: Optional[dict] = None
    ) -> str:
        """
        テキスト翻訳

        Args:
            source_text: 日本語マークダウン
            target_language: 翻訳先言語コード (en, zh, ko, etc.)
            context: 追加コンテキスト（レイアウト情報等）

        Returns:
            翻訳されたマークダウン
        """
        pass
