"""
ダウンロードAPIの統合テスト
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def sample_output_id():
    """テスト用出力ID"""
    return str(uuid4())


@pytest.fixture
def sample_job_id():
    """テスト用ジョブID"""
    return str(uuid4())


@pytest.fixture
def mock_completed_output(sample_output_id, sample_job_id):
    """モック完了済み翻訳出力"""
    return {
        "id": sample_output_id,
        "job_id": sample_job_id,
        "target_language": "en",
        "translator_engine": "claude",
        "status": "completed",
        "translated_markdown_url": "https://example.com/translated.md"
    }


@pytest.fixture
def mock_job_data(sample_job_id):
    """モックジョブデータ"""
    return {
        "id": sample_job_id,
        "ocr_status": "completed",
        "japanese_markdown_url": "https://example.com/master.md",
        "layout_metadata": {"writing_mode": "horizontal", "columns": 1}
    }


@pytest.mark.integration
class TestDownloadMarkdownAPI:
    """マークダウンダウンロードAPIのテスト"""

    @patch('app.api.download.get_supabase_admin_client')
    @patch('app.api.download.httpx.AsyncClient')
    async def test_download_markdown_success(
        self,
        mock_httpx,
        mock_supabase,
        client,
        sample_output_id,
        mock_completed_output
    ):
        """download_markdown - 成功ケース"""
        # Supabaseモック
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        output_response = MagicMock()
        output_response.data = mock_completed_output
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = output_response

        # HTTPXモック
        mock_http_client = AsyncMock()
        mock_http_response = AsyncMock()
        mock_http_response.content = b"# Translated content"
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_http_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client

        response = client.get(f"/api/download/{sample_output_id}/markdown")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

    @patch('app.api.download.get_supabase_admin_client')
    def test_download_markdown_not_found(
        self,
        mock_supabase,
        client,
        sample_output_id
    ):
        """download_markdown - 出力が見つからない"""
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        output_response = MagicMock()
        output_response.data = None
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = output_response

        response = client.get(f"/api/download/{sample_output_id}/markdown")

        assert response.status_code == 404

    @patch('app.api.download.get_supabase_admin_client')
    def test_download_markdown_not_completed(
        self,
        mock_supabase,
        client,
        sample_output_id,
        mock_completed_output
    ):
        """download_markdown - 翻訳未完了"""
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # ステータスを未完了に変更
        incomplete_output = mock_completed_output.copy()
        incomplete_output["status"] = "processing"

        output_response = MagicMock()
        output_response.data = incomplete_output
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = output_response

        response = client.get(f"/api/download/{sample_output_id}/markdown")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]


@pytest.mark.integration
class TestDownloadHTMLAPI:
    """HTMLダウンロードAPIのテスト"""

    @patch('app.api.download.HTMLGenerator')
    @patch('app.api.download.get_supabase_admin_client')
    @patch('app.api.download.httpx.AsyncClient')
    async def test_download_html_success(
        self,
        mock_httpx,
        mock_supabase,
        mock_html_gen_class,
        client,
        sample_output_id,
        mock_completed_output,
        mock_job_data
    ):
        """download_html - 成功ケース"""
        # Supabaseモック
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        output_response = MagicMock()
        output_response.data = mock_completed_output

        job_response = MagicMock()
        job_response.data = mock_job_data

        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            output_response,
            job_response
        ]

        # HTTPXモック
        mock_http_client = AsyncMock()
        mock_http_response = AsyncMock()
        mock_http_response.text = "# Translated content"
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_http_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client

        # HTMLGeneratorモック
        mock_html_gen = MagicMock()
        mock_html_gen.generate_html.return_value = "<html>Generated HTML</html>"
        mock_html_gen_class.return_value = mock_html_gen

        response = client.get(f"/api/download/{sample_output_id}/html")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"


@pytest.mark.integration
class TestDownloadPDFAPI:
    """PDFダウンロードAPIのテスト"""

    @patch('app.api.download.PDFGenerator')
    @patch('app.api.download.get_supabase_admin_client')
    @patch('app.api.download.httpx.AsyncClient')
    async def test_download_pdf_success(
        self,
        mock_httpx,
        mock_supabase,
        mock_pdf_gen_class,
        client,
        sample_output_id,
        mock_completed_output,
        mock_job_data
    ):
        """download_pdf - 成功ケース"""
        # Supabaseモック
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        output_response = MagicMock()
        output_response.data = mock_completed_output

        job_response = MagicMock()
        job_response.data = mock_job_data

        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
            output_response,
            job_response
        ]

        # HTTPXモック
        mock_http_client = AsyncMock()
        mock_http_response = AsyncMock()
        mock_http_response.text = "# Translated content"
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_http_response
        mock_httpx.return_value.__aenter__.return_value = mock_http_client

        # PDFGeneratorモック
        mock_pdf_gen = MagicMock()
        mock_pdf_gen.generate_pdf_from_markdown.return_value = b"%PDF-1.4 Generated PDF"
        mock_pdf_gen_class.return_value = mock_pdf_gen

        response = client.get(f"/api/download/{sample_output_id}/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
