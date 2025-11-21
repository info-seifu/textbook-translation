"""
OCRオーケストレーター
PDF全体のOCR処理を管理
"""
from typing import List, Dict, Tuple
import json
import re
from pathlib import Path
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.pdf_image_extractor import PDFImageExtractor
from app.models.schemas import OCRResult


class OCROrchestrator:
    """OCR処理全体の管理"""

    def __init__(self, gemini_service: GeminiOCRService, db_client):
        self.gemini = gemini_service
        self.db_client = db_client
        self.image_extractor = PDFImageExtractor()

    @staticmethod
    def _has_heading_at_start(markdown_text: str) -> bool:
        """
        Markdownテキストの先頭に見出しがあるかチェック

        Args:
            markdown_text: チェック対象のMarkdownテキスト

        Returns:
            見出しがある場合True
        """
        if not markdown_text:
            return False

        # 先頭の空白行をスキップ
        lines = markdown_text.strip().split('\n')
        if not lines:
            return False

        first_line = lines[0].strip()

        # Markdown見出し記号（# ## ###）で始まる
        if re.match(r'^#{1,6}\s+\S', first_line):
            return True

        # HTMLタグの見出し（<h1> <h2> <h3>）
        if re.match(r'^<h[1-6][^>]*>.*?</h[1-6]>', first_line):
            return True

        return False

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

        # 2. マークダウン統合（Phase 2: セクションメタデータも生成）
        full_markdown, sections_metadata = self._merge_markdown(ocr_results)

        # 3. マスターマークダウンをStorageに保存
        markdown_url = await self._save_markdown(job_id, full_markdown)

        # 4. 図表を画像として抽出（Phase 1）
        figures_metadata = await self._extract_figures(
            job_id, pdf_path, ocr_results
        )

        # 5. セクションメタデータを図表情報とマージ
        sections_with_figures = self._merge_section_and_figure_metadata(
            sections_metadata, figures_metadata
        )

        # 6. メタデータをDBに保存
        await self._save_metadata(
            job_id, ocr_results, markdown_url,
            figures_metadata, sections_with_figures
        )

        return markdown_url

    def _merge_markdown(
        self,
        ocr_results: List[OCRResult]
    ) -> Tuple[str, List[Dict]]:
        """
        各ページのマークダウンを統合（Phase 2改善版）

        Returns:
            (統合マークダウン, セクションメタデータ)
        """

        markdown_parts = []
        sections = []

        for i, result in enumerate(ocr_results):
            page_num = result.page_number

            # ページ見出しをセクションとして扱う
            section_id = f"page-{page_num}"

            # 見出しベースの改ページ制御:
            # - 最初のページは常に改ページマーカーを挿入
            # - 2ページ目以降は、見出しがある場合のみ改ページマーカーを挿入
            if i == 0 or self._has_heading_at_start(result.markdown_text):
                markdown_parts.append(
                    f'<div id="{section_id}" class="page-break-marker"></div>\n\n'
                )

            # セクション情報を記録
            section_info = {
                "id": section_id,
                "title_ja": f"ページ {page_num}",
                "title_en": None,
                "original_pages": [page_num],
                "translated_pages": None,
                "figures": []
            }

            # 本文を追加
            markdown_parts.append(result.markdown_text)
            markdown_parts.append("\n\n")

            # 図表参照を挿入
            for fig in result.figures:
                fig_id = f"page_{page_num}_fig_{fig.id}"
                section_info["figures"].append(fig_id)

                # Phase 2: 図表参照をMarkdown画像記法で挿入
                caption = fig.description if fig.description else f"図{fig.id}"
                markdown_parts.append(
                    f"![{caption}](figures/{fig_id}.png)\n\n"
                )
                if fig.description:
                    markdown_parts.append(f"*{caption}*\n\n")

            sections.append(section_info)

        merged_markdown = ''.join(markdown_parts)
        return merged_markdown, sections

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

    def _merge_section_and_figure_metadata(
        self,
        sections: List[Dict],
        figures: List[Dict]
    ) -> List[Dict]:
        """
        セクションメタデータと図表メタデータをマージ

        Args:
            sections: セクション情報リスト
            figures: 図表メタデータリスト

        Returns:
            図表情報を含むセクションメタデータ
        """
        # 図表をページごとにグループ化
        figures_by_page = {}
        for fig in figures:
            page = fig.get("page", 1)
            if page not in figures_by_page:
                figures_by_page[page] = []
            figures_by_page[page].append(fig)

        # セクションに図表のsection_idを設定
        for section in sections:
            original_pages = section.get("original_pages", [])
            section_id = section.get("id", "")

            # このセクションに含まれる図表を収集
            section_figures = []
            for page in original_pages:
                page_figures = figures_by_page.get(page, [])
                for fig in page_figures:
                    # 図表にsection_idを追加
                    fig["section_id"] = section_id
                    section_figures.append(fig["id"])

            # セクションの図表リストを更新
            section["figures"] = section_figures

        return sections

    async def _extract_figures(
        self,
        job_id: str,
        pdf_path: str,
        ocr_results: List[OCRResult]
    ) -> List[dict]:
        """
        PDFから図表を画像として抽出

        Args:
            job_id: ジョブID
            pdf_path: PDFファイルパス
            ocr_results: OCR結果リスト

        Returns:
            抽出した図表のメタデータリスト
        """
        # OCR結果から図表情報を収集
        figures_to_extract = []
        for result in ocr_results:
            for fig in result.figures:
                figures_to_extract.append({
                    'page': result.page_number,
                    'id': fig.id,
                    'position': {
                        'x': fig.position.x,
                        'y': fig.position.y,
                        'width': fig.position.width,
                        'height': fig.position.height
                    },
                    'type': fig.type,
                    'description': fig.description
                })

        if not figures_to_extract:
            return []

        # ローカルストレージのディレクトリパスを取得
        # PDFパスから親ディレクトリを取得（storage/documents/{job_id}/）
        pdf_path_obj = Path(pdf_path)
        job_dir = pdf_path_obj.parent
        figures_dir = job_dir / 'figures'

        # 図表を抽出
        extracted_figures = self.image_extractor.extract_figures_from_pdf(
            pdf_path=pdf_path,
            figures_metadata=figures_to_extract,
            output_dir=str(figures_dir)
        )

        # メタデータをJSONファイルとして保存
        metadata_path = figures_dir / 'metadata.json'
        metadata = {
            'figures': extracted_figures
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return extracted_figures

    async def _save_metadata(
        self,
        job_id: str,
        ocr_results: List[OCRResult],
        markdown_url: str,
        figures_metadata: List[dict] = None,
        sections_metadata: List[dict] = None
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

        # Phase 2: セクション情報を追加
        if sections_metadata:
            layout_metadata['sections'] = sections_metadata

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

        # Phase 1: 抽出した図表のメタデータを追加
        if figures_metadata:
            figures_data['extracted_figures'] = figures_metadata

        self.db_client.table('translation_jobs').update({
            'layout_metadata': layout_metadata,
            'figures_data': figures_data,
            'page_count': len(ocr_results),
            'japanese_markdown_url': markdown_url,
            'ocr_status': 'completed'
        }).eq('id', job_id).execute()
