"""
HTMLジェネレーターのテスト
"""
import pytest

from app.services.html_generator import HTMLGenerator


@pytest.fixture
def html_generator():
    """HTMLジェネレーター"""
    return HTMLGenerator()


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
class TestHTMLGenerator:
    """HTMLジェネレーターのテスト"""

    def test_generate_html_basic(
        self,
        html_generator,
        sample_markdown,
        sample_layout_metadata
    ):
        """generate_html - 基本HTML生成"""
        html = html_generator.generate_html(
            sample_markdown,
            sample_layout_metadata,
            "en",
            "test-job-id"
        )

        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "chapter 1" in html.lower()
        assert "</html>" in html.lower()

    def test_generate_html_with_vertical_writing(
        self,
        html_generator,
        sample_markdown
    ):
        """generate_html - 縦書きHTML生成"""
        vertical_metadata = {
            "writing_mode": "vertical",
            "columns": 1,
            "primary_direction": "vertical"
        }

        html = html_generator.generate_html(
            sample_markdown,
            vertical_metadata,
            "ja",
            "test-job-id"
        )

        assert isinstance(html, str)
        # 縦書き関連のCSSが含まれているかチェック
        assert "writing-mode" in html.lower() or "vertical" in html.lower()

    def test_generate_html_empty_markdown(
        self,
        html_generator,
        sample_layout_metadata
    ):
        """generate_html - 空のMarkdown"""
        html = html_generator.generate_html(
            "",
            sample_layout_metadata,
            "en",
            "test-job-id"
        )

        assert isinstance(html, str)
        assert "<html" in html.lower()

    def test_generate_html_with_images(
        self,
        html_generator,
        sample_layout_metadata
    ):
        """generate_html - 画像付きMarkdown"""
        markdown_with_images = """# Test

![Figure 1](figures/test.png)

Some content.
"""

        html = html_generator.generate_html(
            markdown_with_images,
            sample_layout_metadata,
            "en",
            "test-job-id"
        )

        assert isinstance(html, str)
        assert "img" in html.lower() or "figure" in html.lower()
