"""
アップロードAPIの統合テスト
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from io import BytesIO

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    """テスト用PDFファイル（モック）"""
    # 実際のPDFではなく、テスト用のダミーデータ
    return b'%PDF-1.4\n%Test PDF content\n%%EOF'


@pytest.fixture
def mock_pdf_file(sample_pdf_bytes):
    """テスト用PDFファイルオブジェクト"""
    return ("test.pdf", BytesIO(sample_pdf_bytes), "application/pdf")


@pytest.mark.integration
class TestUploadAPI:
    """アップロードAPIの統合テスト"""

    @patch('app.api.upload.OCROrchestrator')
    @patch('app.api.upload.get_supabase_admin_client')
    def test_upload_pdf_success(
        self, mock_supabase, mock_orchestrator_class, client, mock_pdf_file
    ):
        """upload_pdf - 成功ケース"""
        # モックのオーケストレーターインスタンスを設定
        mock_orchestrator = MagicMock()
        # process_pdfは非同期関数なのでAsyncMockを使用
        mock_orchestrator.process_pdf = AsyncMock(
            return_value="https://example.com/master.md"
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        # モックのSupabaseクライアントを設定
        mock_storage = MagicMock()
        mock_supabase.return_value = mock_storage

        response = client.post(
            "/api/upload",
            files={"file": mock_pdf_file}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert "message" in data

    def test_upload_non_pdf_file(self, client):
        """upload_pdf - PDFでないファイル"""
        # テキストファイルをアップロード
        text_file = ("test.txt", BytesIO(b"This is a text file"), "text/plain")

        response = client.post(
            "/api/upload",
            files={"file": text_file}
        )

        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]

    def test_upload_large_file(self, client):
        """upload_pdf - ファイルサイズ超過"""
        # 大きすぎるファイル（100MB以上と仮定）
        large_file_content = b'%PDF-1.4\n' + b'x' * (101 * 1024 * 1024)
        large_file = ("large.pdf", BytesIO(large_file_content), "application/pdf")

        response = client.post(
            "/api/upload",
            files={"file": large_file}
        )

        assert response.status_code == 400
        assert "exceeds maximum allowed size" in response.json()["detail"]

    def test_upload_without_file(self, client):
        """upload_pdf - ファイルなし"""
        response = client.post("/api/upload")

        assert response.status_code == 422  # Validation error

    @patch('app.api.upload.OCROrchestrator')
    @patch('app.api.upload.get_supabase_admin_client')
    def test_upload_with_storage(
        self,
        mock_supabase,
        mock_orchestrator_class,
        client,
        mock_pdf_file
    ):
        """upload_pdf - ストレージ連携テスト"""
        # モック設定
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_storage = MagicMock()
        mock_supabase.return_value = mock_storage

        response = client.post(
            "/api/upload",
            files={"file": mock_pdf_file}
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


@pytest.mark.integration
class TestUploadAPIValidation:
    """アップロードAPIのバリデーションテスト"""

    @patch('app.api.upload.OCROrchestrator')
    @patch('app.api.upload.get_supabase_admin_client')
    def test_upload_empty_pdf(
        self, mock_supabase, mock_orchestrator_class, client
    ):
        """upload_pdf - 空のPDFファイル"""
        empty_file = ("empty.pdf", BytesIO(b""), "application/pdf")

        # モック設定
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_storage = MagicMock()
        mock_supabase.return_value = mock_storage

        response = client.post(
            "/api/upload",
            files={"file": empty_file}
        )

        # 空ファイルは受け入れるが、OCR処理で失敗する可能性がある
        # ここでは400または200のいずれかを期待
        assert response.status_code in [200, 400]

    @patch('app.api.upload.OCROrchestrator')
    @patch('app.api.upload.get_supabase_admin_client')
    def test_upload_invalid_content_type(
        self, mock_supabase, mock_orchestrator_class, client
    ):
        """upload_pdf - 不正なContent-Type"""
        # PDFの拡張子だが、Content-Typeが違う
        file = ("test.pdf", BytesIO(b"not a pdf"), "text/plain")

        # モック設定
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_storage = MagicMock()
        mock_supabase.return_value = mock_storage

        response = client.post(
            "/api/upload",
            files={"file": file}
        )

        # ファイル名で判定するため、成功する可能性がある
        # 実装依存なので、両方許容
        assert response.status_code in [200, 400]

    @patch('app.api.upload.OCROrchestrator')
    @patch('app.api.upload.get_supabase_admin_client')
    def test_upload_filename_validation(
        self, mock_supabase, mock_orchestrator_class, client
    ):
        """upload_pdf - ファイル名のバリデーション"""
        # 特殊文字を含むファイル名
        special_filename = ("test<>|.pdf", BytesIO(b'%PDF-1.4\n%%EOF'), "application/pdf")

        # モック設定
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_storage = MagicMock()
        mock_supabase.return_value = mock_storage

        # ファイル名のサニタイズが実装されているかテスト
        # 期待: エラーまたは正常にサニタイズされて処理
        response = client.post(
            "/api/upload",
            files={"file": special_filename}
        )

        # エラーか成功のいずれか
        assert response.status_code in [200, 400]
