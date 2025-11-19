"""
アプリケーション設定管理
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """アプリケーション設定"""

    # API Keys
    GEMINI_API_KEY: str
    CLAUDE_API_KEY: str

    # Supabase (オプショナル - ローカル動作時は不要)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Backend
    BACKEND_PORT: int = 8000
    BACKEND_HOST: str = "0.0.0.0"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # Gemini Settings
    # USE_GEMINI_3: true = Gemini 3.0 Pro (requires billing), false = Gemini 2.5 (free tier)
    USE_GEMINI_3: bool = False

    # Gemini 2.5 Models (Free tier)
    GEMINI_2_5_OCR_MODEL: str = "gemini-2.5-pro"
    GEMINI_2_5_TRANSLATE_MODEL: str = "gemini-2.5-flash"

    # Gemini 3.0 Models (Requires billing account)
    GEMINI_3_OCR_MODEL: str = "gemini-3-pro-preview"
    GEMINI_3_TRANSLATE_MODEL: str = "gemini-3-pro-preview"

    @property
    def gemini_ocr_model(self) -> str:
        """OCR用モデル名（USE_GEMINI_3により切り替え）"""
        return self.GEMINI_3_OCR_MODEL if self.USE_GEMINI_3 else self.GEMINI_2_5_OCR_MODEL

    @property
    def gemini_translate_model(self) -> str:
        """翻訳用モデル名（USE_GEMINI_3により切り替え）"""
        return self.GEMINI_3_TRANSLATE_MODEL if self.USE_GEMINI_3 else self.GEMINI_2_5_TRANSLATE_MODEL

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_origins_list(self) -> List[str]:
        """CORS許可オリジンのリスト"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """最大ファイルサイズ（バイト）"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


# グローバル設定インスタンス
settings = Settings()
