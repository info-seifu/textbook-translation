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
