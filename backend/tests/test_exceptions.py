"""
例外クラスのテスト
"""
import pytest
from app.exceptions import (
    AppException,
    OCRException,
    TranslationException,
    APIRateLimitException,
    APIException
)


@pytest.mark.unit
class TestExceptions:
    """カスタム例外クラスのテスト"""

    def test_app_exception_basic(self):
        """AppException - 基本的な例外"""
        exc = AppException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_app_exception_with_details(self):
        """AppException - 詳細情報付き"""
        details = {"key": "value", "count": 42}
        exc = AppException("Test error", details=details)

        assert exc.message == "Test error"
        assert exc.details == details
        assert exc.details["key"] == "value"
        assert exc.details["count"] == 42

    def test_ocr_exception(self):
        """OCRException - OCR処理例外"""
        details = {"page": 5, "error": "Image too large"}
        exc = OCRException("OCR failed", details=details)

        assert isinstance(exc, AppException)
        assert exc.message == "OCR failed"
        assert exc.details["page"] == 5
        assert exc.details["error"] == "Image too large"

    def test_translation_exception(self):
        """TranslationException - 翻訳処理例外"""
        details = {"source_lang": "en", "target_lang": "ja"}
        exc = TranslationException("Translation failed", details=details)

        assert isinstance(exc, AppException)
        assert exc.message == "Translation failed"
        assert exc.details["source_lang"] == "en"

    def test_api_rate_limit_exception_basic(self):
        """APIRateLimitException - retry_afterなし"""
        exc = APIRateLimitException("Rate limit exceeded")

        assert isinstance(exc, AppException)
        assert exc.message == "Rate limit exceeded"
        assert exc.retry_after is None

    def test_api_rate_limit_exception_with_retry_after(self):
        """APIRateLimitException - retry_after付き"""
        exc = APIRateLimitException(
            "Rate limit exceeded",
            retry_after=60,
            details={"limit": 100, "used": 100}
        )

        assert exc.message == "Rate limit exceeded"
        assert exc.retry_after == 60
        assert exc.details["limit"] == 100
        assert exc.details["used"] == 100

    def test_api_exception_basic(self):
        """APIException - 基本的なAPI例外"""
        exc = APIException("API call failed")

        assert isinstance(exc, AppException)
        assert exc.message == "API call failed"
        assert exc.status_code is None

    def test_api_exception_with_status_code(self):
        """APIException - ステータスコード付き"""
        exc = APIException(
            "API call failed",
            status_code=503,
            details={"service": "gemini", "endpoint": "/v1/chat"}
        )

        assert exc.message == "API call failed"
        assert exc.status_code == 503
        assert exc.details["service"] == "gemini"

    def test_exception_inheritance_chain(self):
        """例外の継承チェーン確認"""
        ocr_exc = OCRException("OCR error")
        trans_exc = TranslationException("Translation error")
        rate_limit_exc = APIRateLimitException("Rate limit")
        api_exc = APIException("API error")

        # すべてAppExceptionを継承
        assert isinstance(ocr_exc, AppException)
        assert isinstance(trans_exc, AppException)
        assert isinstance(rate_limit_exc, AppException)
        assert isinstance(api_exc, AppException)

        # すべてExceptionを継承
        assert isinstance(ocr_exc, Exception)
        assert isinstance(trans_exc, Exception)
        assert isinstance(rate_limit_exc, Exception)
        assert isinstance(api_exc, Exception)

    def test_exception_can_be_raised_and_caught(self):
        """例外がraise/catchできることを確認"""
        # OCRException
        with pytest.raises(OCRException, match="OCR failed"):
            raise OCRException("OCR failed", details={"page": 1})

        # TranslationException
        with pytest.raises(TranslationException, match="Translation failed"):
            raise TranslationException("Translation failed")

        # APIRateLimitException
        with pytest.raises(APIRateLimitException, match="Rate limit"):
            raise APIRateLimitException("Rate limit", retry_after=30)

        # APIException
        with pytest.raises(APIException, match="API error"):
            raise APIException("API error", status_code=500)

    def test_catch_as_base_exception(self):
        """基底例外としてcatchできることを確認"""
        try:
            raise OCRException("OCR error", details={"page": 3})
        except AppException as e:
            assert e.message == "OCR error"
            assert e.details["page"] == 3
        else:
            pytest.fail("Exception was not caught")
