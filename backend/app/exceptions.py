"""
カスタム例外クラス

アプリケーション全体で使用する例外を定義
"""


class AppException(Exception):
    """アプリケーション基底例外"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class OCRException(AppException):
    """OCR処理関連の例外"""
    pass


class TranslationException(AppException):
    """翻訳処理関連の例外"""
    pass


class StorageException(AppException):
    """ストレージ操作関連の例外"""
    pass


class APIRateLimitException(AppException):
    """APIレート制限例外"""

    def __init__(
        self,
        message: str,
        retry_after: int = None,
        details: dict = None
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class APIException(AppException):
    """API呼び出し関連の例外"""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        details: dict = None
    ):
        super().__init__(message, details)
        self.status_code = status_code
