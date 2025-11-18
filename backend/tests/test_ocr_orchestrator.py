"""
OCRオーケストレーターのテスト
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from app.services.ocr_orchestrator import OCROrchestrator
from app.services.gemini_ocr_service import GeminiOCRService
from app.models.schemas import OCRResult, LayoutInfo, FigureData, FigurePosition


@pytest.fixture
def mock_gemini_service():
    """モックGemini OCRサービス"""
    return MagicMock(spec=GeminiOCRService)


@pytest.fixture
def mock_db_client():
    """モックデータベースクライアント"""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value = mock_table
    return mock_client


@pytest.fixture
def orchestrator(mock_gemini_service, mock_db_client):
    """OCRオーケストレーター"""
    return OCROrchestrator(mock_gemini_service, mock_db_client)


@pytest.fixture
def sample_ocr_result():
    """サンプルOCR結果"""
    return OCRResult(
        page_number=1,
        markdown_text="# テストページ\n\nテスト内容です。",
        figures=[],
        layout_info=LayoutInfo(
            primary_direction="horizontal",
            columns=1,
            has_ruby=False,
            special_elements=[],
            mixed_regions=[]
        ),
        detected_writing_mode="horizontal"
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestOCROrchestrator:
    """OCRオーケストレーターのテスト"""

    def test_merge_markdown(self, orchestrator, sample_ocr_result):
        """_merge_markdown - マークダウン統合"""
        ocr_results = [sample_ocr_result, sample_ocr_result]
        ocr_results[1].page_number = 2

        merged = orchestrator._merge_markdown(ocr_results)

        assert "ページ 1" in merged
        assert "ページ 2" in merged
        assert "テストページ" in merged

    def test_merge_markdown_with_figures(self, orchestrator, sample_ocr_result):
        """_merge_markdown - 図解付きマークダウン統合"""
        figure = FigureData(
            id=1,
            position=FigurePosition(x=100, y=100, width=200, height=150),
            type="photo",
            description="テスト図",
            extracted_text=None
        )
        sample_ocr_result.figures = [figure]

        merged = orchestrator._merge_markdown([sample_ocr_result])

        assert "![図1](figures/page1_fig1.png)" in merged

    @patch('app.services.ocr_orchestrator.pdf_to_images')
    async def test_process_pdf_basic(
        self,
        mock_pdf_to_images,
        orchestrator,
        mock_gemini_service,
        sample_ocr_result
    ):
        """process_pdf - 基本処理フロー"""
        # モック設定
        mock_pdf_to_images.return_value = [b'page1', b'page2']
        mock_gemini_service.extract_page = AsyncMock(return_value=sample_ocr_result)

        # プライベートメソッドをモック化
        orchestrator._process_figures = AsyncMock()
        orchestrator._save_markdown = AsyncMock(return_value="https://example.com/master.md")
        orchestrator._save_metadata = AsyncMock()

        job_id = str(uuid4())
        result_url = await orchestrator.process_pdf(job_id, "/tmp/test.pdf")

        assert result_url == "https://example.com/master.md"
        assert mock_gemini_service.extract_page.call_count == 2
        orchestrator._process_figures.assert_called_once()
        orchestrator._save_markdown.assert_called_once()
        orchestrator._save_metadata.assert_called_once()


@pytest.mark.unit
class TestOCROrchestratorMerge:
    """OCRオーケストレーターのマージ機能テスト"""

    def test_merge_empty_results(self, orchestrator):
        """_merge_markdown - 空の結果"""
        merged = orchestrator._merge_markdown([])
        assert merged == ""

    def test_merge_single_page(self, orchestrator, sample_ocr_result):
        """_merge_markdown - 単一ページ"""
        merged = orchestrator._merge_markdown([sample_ocr_result])
        assert "ページ 1" in merged
        assert "テストページ" in merged
