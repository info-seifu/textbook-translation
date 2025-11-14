"""
エラーハンドリング
"""
from fastapi import HTTPException, status
from typing import Optional


class OCRError(Exception):
    """OCR処理エラー"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TranslationError(Exception):
    """翻訳処理エラー"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileProcessingError(Exception):
    """ファイル処理エラー"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


def raise_bad_request(message: str):
    """400 Bad Requestを発生させる"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def raise_not_found(message: str):
    """404 Not Foundを発生させる"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=message
    )


def raise_internal_error(message: str):
    """500 Internal Server Errorを発生させる"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )
