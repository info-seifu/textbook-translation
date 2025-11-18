"""
PDFジェネレーターのテスト
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.pdf_generator import PDFGenerator


@pytest.fixture
def pdf_generator():
    """PDFジェネレーター"""
    return PDFGenerator()


@pytest.fixture
def sample_markdown():
    """サンプルMarkdown"""
    return """# Chapter 1

This is a test chapter.

## Section 1.1

Content here.
"""


@pytest.fixture
def sample_layout_metadata():
    """サンプルレイアウトメタデータ"""
    return {
        "writing_mode": "horizontal",
        "columns": 1,
        "primary_direction": "horizontal"
    }


@pytest.mark.unit
class TestPDFGenerator:
    """PDFジェネレーターのテスト"""

    @patch('app.services.pdf_generator.HTML')
    def test_generate_pdf_from_markdown_basic(
        self,
        mock_html_class,
        pdf_generator,
        sample_markdown,
        sample_layout_metadata
    ):
        """generate_pdf_from_markdown - 基本PDF生成"""
        # モックHTML
        mock_html = MagicMock()
        mock_html.write_pdf.return_value = b'%PDF-1.4 test content'
        mock_html_class.return_value = mock_html

        pdf_bytes = pdf_generator.generate_pdf_from_markdown(
            sample_markdown,
            sample_layout_metadata,
            "en",
            "test-job-id"
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b'%PDF') or len(pdf_bytes) > 0

    @patch('app.services.pdf_generator.HTML')
    def test_generate_pdf_empty_markdown(
        self,
        mock_html_class,
        pdf_generator,
        sample_layout_metadata
    ):
        """generate_pdf_from_markdown - 空のMarkdown"""
        mock_html = MagicMock()
        mock_html.write_pdf.return_value = b'%PDF-1.4'
        mock_html_class.return_value = mock_html

        pdf_bytes = pdf_generator.generate_pdf_from_markdown(
            "",
            sample_layout_metadata,
            "en",
            "test-job-id"
        )

        assert isinstance(pdf_bytes, bytes)

    @patch('app.services.pdf_generator.HTML')
    def test_generate_pdf_with_vertical_writing(
        self,
        mock_html_class,
        pdf_generator,
        sample_markdown
    ):
        """generate_pdf_from_markdown - 縦書きPDF生成"""
        vertical_metadata = {
            "writing_mode": "vertical",
            "columns": 1,
            "primary_direction": "vertical"
        }

        mock_html = MagicMock()
        mock_html.write_pdf.return_value = b'%PDF-1.4 vertical'
        mock_html_class.return_value = mock_html

        pdf_bytes = pdf_generator.generate_pdf_from_markdown(
            sample_markdown,
            vertical_metadata,
            "ja",
            "test-job-id"
        )

        assert isinstance(pdf_bytes, bytes)
