"""
OCRオーケストレーター
PDF全体のOCR処理を管理
"""
from typing import List
import asyncio
from app.services.gemini_ocr_service import GeminiOCRService
from app.models.schemas import OCRResult


class OCROrchestrator:
    """OCR処理全体の管理"""

    def __init__(self, gemini_service: GeminiOCRService, db_client):
        self.gemini = gemini_service
        self.db_client = db_client

    async def process_pdf(
        self,
        job_id: str,
        pdf_path: str
    ) -> str:
        """
        PDF全体のOCR処理（PDF直接送信方式）

        Args:
            job_id: ジョブID
            pdf_path: PDFファイルパス

        Returns:
            日本語マークダウンのURL
        """

        # 処理中ステータスに更新
        self.db_client.table('translation_jobs').update({
            'ocr_status': 'processing'
        }).eq('id', job_id).execute()

        # 1. PDFを直接Geminiに送信してOCR処理
        ocr_results = await self.gemini.extract_from_pdf(pdf_path)
        page_count = len(ocr_results)

        # ページ数をDBに記録
        self.db_client.table('translation_jobs').update({
            'page_count': page_count
        }).eq('id', job_id).execute()

        # 2. マークダウン統合
        full_markdown = self._merge_markdown(ocr_results)

        # 3. マスターマークダウンをStorageに保存
        markdown_url = await self._save_markdown(job_id, full_markdown)

        # 4. メタデータをDBに保存
        await self._save_metadata(job_id, ocr_results, markdown_url)

        # 注意: 図解の切り取りはPDF直接送信方式では行わない
        # 必要であれば後で追加実装可能

        return markdown_url

    def _merge_markdown(self, ocr_results: List[OCRResult]) -> str:
        """各ページのマークダウンを統合"""

        markdown_parts = []

        for result in ocr_results:
            markdown_parts.append(f"# ページ {result.page_number}\n\n")
            markdown_parts.append(result.markdown_text)
            markdown_parts.append("\n\n")

            # 図解参照を挿入
            for fig in result.figures:
                markdown_parts.append(
                    f"![図{fig.id}](figures/page{result.page_number}_fig{fig.id}.png)\n\n"
                )
                if fig.description:
                    markdown_parts.append(f"*{fig.description}*\n\n")

        return ''.join(markdown_parts)


    async def _save_markdown(self, job_id: str, markdown: str) -> str:
        """マスターマークダウンをStorageに保存"""

        file_path = f"{job_id}/master_ja.md"

        try:
            # アップロード
            self.db_client.storage.from_('documents').upload(
                file_path,
                markdown.encode('utf-8'),
                {'content-type': 'text/markdown'}
            )

            # 公開URLを取得
            url = self.db_client.storage.from_('documents').get_public_url(file_path)
            return url

        except Exception as e:
            raise Exception(f"Failed to save markdown: {str(e)}")

    async def _save_metadata(
        self,
        job_id: str,
        ocr_results: List[OCRResult],
        markdown_url: str
    ):
        """レイアウト情報等をDBに保存"""

        layout_metadata = {
            'page_count': len(ocr_results),
            'pages': [
                {
                    'page_number': r.page_number,
                    'detected_writing_mode': r.detected_writing_mode,
                    'layout_info': r.layout_info.model_dump()
                }
                for r in ocr_results
            ]
        }

        figures_data = {
            'total_figures': sum(len(r.figures) for r in ocr_results),
            'pages': [
                {
                    'page_number': r.page_number,
                    'figure_count': len(r.figures)
                }
                for r in ocr_results
            ]
        }

        self.db_client.table('translation_jobs').update({
            'layout_metadata': layout_metadata,
            'figures_data': figures_data,
            'page_count': len(ocr_results),
            'japanese_markdown_url': markdown_url,
            'ocr_status': 'completed'
        }).eq('id', job_id).execute()
