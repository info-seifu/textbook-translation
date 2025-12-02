"""
OCRオーケストレーター
PDF全体のOCR処理を管理
"""
from typing import List
import asyncio
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.layoutlmv3_detector import LayoutLMv3Detector
from app.services.figure_integrator import FigureIntegrator, PagedFigureData
from app.services.pdf_image_extractor import PDFImageExtractor
from app.models.schemas import OCRResult, FigureData

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """OCR処理全体の管理"""

    def __init__(self, gemini_service: GeminiOCRService, db_client):
        self.gemini = gemini_service
        self.db_client = db_client
        self.image_extractor = PDFImageExtractor()

        # LayoutLMv3 ハイブリッド検出の設定
        self.layoutlmv3_enabled = os.getenv("LAYOUTLMV3_ENABLED", "true").lower() == "true"
        self.layoutlmv3_detector = LayoutLMv3Detector() if self.layoutlmv3_enabled else None
        self.figure_integrator = FigureIntegrator() if self.layoutlmv3_enabled else None
        self.executor = ThreadPoolExecutor(max_workers=2)

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

        # 1.5. LayoutLMv3 ハイブリッド検出
        if self.layoutlmv3_enabled and self.layoutlmv3_detector:
            try:
                ocr_results = await self._apply_hybrid_detection(pdf_path, ocr_results)
            except Exception as e:
                logger.warning(f"Hybrid detection failed, using Gemini-only results: {e}")

        # ページ数をDBに記録
        self.db_client.table('translation_jobs').update({
            'page_count': page_count
        }).eq('id', job_id).execute()

        # 2. マークダウン統合
        full_markdown = self._merge_markdown(ocr_results)

        # 3. マスターマークダウンをStorageに保存
        markdown_url = await self._save_markdown(job_id, full_markdown)

        # 4. 図表を画像として抽出
        figures_metadata = await self._extract_figures(
            job_id, pdf_path, ocr_results
        )

        # 5. メタデータをDBに保存
        await self._save_metadata(
            job_id, ocr_results, markdown_url, figures_metadata
        )

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
        markdown_url: str,
        figures_metadata: dict = None
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

        # 図表メタデータを統合
        if figures_metadata:
            figures_data = figures_metadata
        else:
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

    async def _apply_hybrid_detection(
        self,
        pdf_path: str,
        ocr_results: List[OCRResult]
    ) -> List[OCRResult]:
        """
        LayoutLMv3ハイブリッド検出を適用

        Args:
            pdf_path: PDFファイルパス
            ocr_results: Gemini OCRの結果

        Returns:
            ハイブリッド検出結果で更新されたOCR結果
        """
        logger.info("Starting LayoutLMv3 hybrid detection")

        # LayoutLMv3で図表を検出
        loop = asyncio.get_event_loop()
        detector_figures = await loop.run_in_executor(
            self.executor,
            self._run_layoutlmv3_detection,
            pdf_path
        )

        # Gemini図表をPagedFigureDataに変換
        gemini_figures = []
        for result in ocr_results:
            for fig in result.figures:
                gemini_figures.append(
                    PagedFigureData(page=result.page_number, figure=fig)
                )

        # 図表を統合
        integrated_figures = self.figure_integrator.integrate_figures(
            gemini_figures=gemini_figures,
            detector_figures=detector_figures,
            fallback_enabled=True
        )

        # OCR結果を更新
        for result in ocr_results:
            # 該当ページの統合図表を取得
            page_integrated = [
                fig for fig in integrated_figures
                if fig.page == result.page_number
            ]

            # FigureDataに変換して更新
            result.figures = []
            for idx, int_fig in enumerate(page_integrated):
                result.figures.append(FigureData(
                    id=f"fig_{result.page_number}_{idx}",
                    type=int_fig.type,
                    position=int_fig.position,
                    description=int_fig.description
                ))

        logger.info(
            f"Hybrid detection completed: {len(integrated_figures)} total figures"
        )
        return ocr_results

    def _run_layoutlmv3_detection(self, pdf_path: str):
        """
        LayoutLMv3検出を実行（同期処理）

        Args:
            pdf_path: PDFファイルパス

        Returns:
            検出された図表のリスト
        """
        return self.layoutlmv3_detector.detect_figures(pdf_path)

    async def _extract_figures(
        self,
        job_id: str,
        pdf_path: str,
        ocr_results: List[OCRResult]
    ) -> dict:
        """
        検出された図表を画像として抽出し、Storageに保存

        Args:
            job_id: ジョブID
            pdf_path: PDFファイルパス
            ocr_results: OCR結果（図表情報を含む）

        Returns:
            図表メタデータ
        """
        logger.info("Extracting figures as images")

        # 一時ディレクトリを作成
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # 全図表を収集
            all_figures = []
            for result in ocr_results:
                for fig in result.figures:
                    all_figures.append({
                        'page': result.page_number,
                        'figure': fig,
                        'x': int(fig.position.x),
                        'y': int(fig.position.y),
                        'width': int(fig.position.width),
                        'height': int(fig.position.height)
                    })

            # 画像として抽出
            extracted_count = 0
            if all_figures:
                extracted_images = self.image_extractor.extract_figure_images(
                    pdf_path=pdf_path,
                    figures=all_figures,
                    output_dir=temp_dir
                )

                # Storageにアップロード
                for img_path, fig_info in extracted_images:
                    page_num = fig_info['page']
                    fig_id = fig_info['figure'].id

                    storage_path = f"{job_id}/figures/page{page_num}_{fig_id}.png"

                    with open(img_path, 'rb') as f:
                        self.db_client.storage.from_('documents').upload(
                            storage_path,
                            f.read(),
                            {'content-type': 'image/png'}
                        )

                    extracted_count += 1

            logger.info(f"Extracted {extracted_count} figure images")

            # メタデータを作成
            figures_metadata = {
                'total_figures': len(all_figures),
                'extracted_count': extracted_count,
                'pages': []
            }

            for page_num in range(1, len(ocr_results) + 1):
                page_figures = [f for f in all_figures if f['page'] == page_num]
                figures_metadata['pages'].append({
                    'page_number': page_num,
                    'figure_count': len(page_figures),
                    'figures': [
                        {
                            'id': f['figure'].id,
                            'type': f['figure'].type,
                            'description': f['figure'].description
                        }
                        for f in page_figures
                    ]
                })

            return figures_metadata
