"""
OCRオーケストレーター
PDF全体のOCR処理を管理
"""
from typing import List
import asyncio
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.pdf_preprocessor import pdf_to_images
from app.models.schemas import OCRResult, FigureData


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
        PDF全体のOCR処理

        Args:
            job_id: ジョブID
            pdf_path: PDFファイルパス

        Returns:
            日本語マークダウンのURL
        """

        # 1. PDFを画像化
        page_images = pdf_to_images(pdf_path)
        page_count = len(page_images)

        # ページ数をDBに記録
        self.db_client.table('translation_jobs').update({
            'page_count': page_count,
            'ocr_status': 'processing'
        }).eq('id', job_id).execute()

        # 2. 各ページをOCR（並列処理）
        ocr_tasks = [
            self.gemini.extract_page(img, i + 1)
            for i, img in enumerate(page_images)
        ]

        ocr_results = await asyncio.gather(*ocr_tasks)

        # 3. マークダウン統合
        full_markdown = self._merge_markdown(ocr_results)

        # 4. 図解を切り取ってStorageに保存
        await self._process_figures(job_id, page_images, ocr_results)

        # 5. マスターマークダウンをStorageに保存
        markdown_url = await self._save_markdown(job_id, full_markdown)

        # 6. メタデータをDBに保存
        await self._save_metadata(job_id, ocr_results, markdown_url)

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

    async def _process_figures(
        self,
        job_id: str,
        page_images: List[bytes],
        ocr_results: List[OCRResult]
    ):
        """図解を切り取り、Storageに保存、DBに記録"""

        for result in ocr_results:
            page_num = result.page_number
            page_image = page_images[page_num - 1]

            if not result.figures:
                continue

            # 図解の位置情報を抽出
            figure_positions = [fig.position for fig in result.figures]

            # 図解を切り取り
            figure_images = await self.gemini.extract_figures_from_image(
                page_image,
                figure_positions
            )

            # 各図解を保存
            for fig, fig_img in zip(result.figures, figure_images):
                # Supabase Storageに保存
                file_path = f"{job_id}/figures/page{page_num}_fig{fig.id}.png"

                try:
                    # アップロード
                    self.db_client.storage.from_('figures').upload(
                        file_path,
                        fig_img,
                        {'content-type': 'image/png'}
                    )

                    # 公開URLを取得
                    image_url = self.db_client.storage.from_('figures').get_public_url(file_path)

                    # DBに記録
                    self.db_client.table('figures').insert({
                        'job_id': job_id,
                        'page_number': page_num,
                        'figure_number': fig.id,
                        'image_url': image_url,
                        'bounding_box': {
                            'x': fig.position.x,
                            'y': fig.position.y,
                            'width': fig.position.width,
                            'height': fig.position.height
                        },
                        'description': fig.description,
                        'extracted_text': fig.extracted_text
                    }).execute()

                except Exception as e:
                    print(f"Failed to save figure: {str(e)}")
                    # エラーがあっても続行

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
