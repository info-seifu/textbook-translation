"""
ステータスAPIの統合テスト
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def sample_job_id():
    """テスト用ジョブID"""
    return str(uuid4())


@pytest.fixture
def sample_output_id():
    """テスト用出力ID"""
    return str(uuid4())


@pytest.fixture
def mock_job_data(sample_job_id):
    """モックジョブデータ"""
    return {
        "id": sample_job_id,
        "original_filename": "test.pdf",
        "pdf_url": "https://example.com/test.pdf",
        "page_count": 10,
        "ocr_status": "completed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@pytest.fixture
def mock_translation_output(sample_output_id, sample_job_id):
    """モック翻訳出力データ"""
    return {
        "id": sample_output_id,
        "job_id": sample_job_id,
        "target_language": "en",
        "translator_engine": "claude",
        "status": "completed",
        "created_at": datetime.now().isoformat()
    }


@pytest.mark.integration
class TestStatusAPI:
    """ステータスAPIの統合テスト"""

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_job_status_success(
        self,
        mock_supabase,
        client,
        sample_job_id,
        mock_job_data,
        mock_translation_output
    ):
        """get_job_status - 成功ケース"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # ジョブデータのモック
        job_response = MagicMock()
        job_response.data = mock_job_data
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = job_response

        # 翻訳出力のモック
        outputs_response = MagicMock()
        outputs_response.data = [mock_translation_output]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = outputs_response

        response = client.get(f"/api/jobs/{sample_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "job" in data
        assert "translations" in data
        assert data["job"]["id"] == sample_job_id

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_job_status_not_found(self, mock_supabase, client, sample_job_id):
        """get_job_status - ジョブが見つからない"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # データなしのレスポンス
        job_response = MagicMock()
        job_response.data = None
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = job_response

        response = client.get(f"/api/jobs/{sample_job_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_job_status_error(self, mock_supabase, client, sample_job_id):
        """get_job_status - データベースエラー"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # エラーを発生させる
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Database error")

        response = client.get(f"/api/jobs/{sample_job_id}")

        assert response.status_code == 500
        assert "Failed to get job status" in response.json()["detail"]

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_output_status_success(
        self,
        mock_supabase,
        client,
        sample_output_id,
        mock_translation_output
    ):
        """get_output_status - 成功ケース"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # 出力データのモック
        output_response = MagicMock()
        output_response.data = mock_translation_output
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = output_response

        response = client.get(f"/api/outputs/{sample_output_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_output_id
        assert data["target_language"] == "en"

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_output_status_not_found(
        self,
        mock_supabase,
        client,
        sample_output_id
    ):
        """get_output_status - 出力が見つからない"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # データなしのレスポンス
        output_response = MagicMock()
        output_response.data = None
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = output_response

        response = client.get(f"/api/outputs/{sample_output_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


@pytest.mark.integration
class TestStatusAPIValidation:
    """ステータスAPIのバリデーションテスト"""

    def test_get_job_status_invalid_uuid(self, client):
        """get_job_status - 不正なUUID"""
        response = client.get("/api/jobs/invalid-uuid")

        # UUIDバリデーションが実装されていれば400、
        # そうでなければ404（データが見つからない）
        assert response.status_code in [400, 404, 500]

    def test_get_output_status_invalid_uuid(self, client):
        """get_output_status - 不正なUUID"""
        response = client.get("/api/outputs/invalid-uuid")

        assert response.status_code in [400, 404, 500]

    @patch('app.api.status.get_supabase_admin_client')
    def test_get_job_status_with_no_translations(
        self,
        mock_supabase,
        client,
        sample_job_id,
        mock_job_data
    ):
        """get_job_status - 翻訳出力がない場合"""
        # モック設定
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client

        # ジョブデータのモック
        job_response = MagicMock()
        job_response.data = mock_job_data
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = job_response

        # 翻訳出力なし
        outputs_response = MagicMock()
        outputs_response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = outputs_response

        response = client.get(f"/api/jobs/{sample_job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["translations"] == []
