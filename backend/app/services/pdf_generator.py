"""
PDF生成サービス
HTMLからPDFを生成
"""
from typing import Optional
import io


class PDFGenerator:
    """HTMLからPDFを生成"""

    def generate_pdf(
        self,
        html_content: str,
        base_url: Optional[str] = None
    ) -> bytes:
        """
        HTMLからPDFを生成

        Args:
            html_content: HTML文字列
            base_url: 相対パス解決用のベースURL

        Returns:
            PDFのバイト列
        """
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise ImportError(
                "weasyprint is not installed. "
                "Please install it with: pip install weasyprint"
            )

        # HTMLオブジェクトを作成
        html_obj = HTML(string=html_content, base_url=base_url)

        # 追加のCSS（PDF最適化用、Phase 4拡張）
        pdf_css = CSS(string="""
            @page {
                size: A4;
                margin: 20mm;

                /* Phase 4: フッターにページ番号を表示 */
                @bottom-center {
                    content: counter(page);
                    font-size: 10pt;
                    color: #666;
                }
            }

            body {
                font-size: 10pt;  /* 11pt -> 10pt に縮小 */
                line-height: 1.4;  /* 行間を狭く（デフォルトは1.6程度） */
            }

            /* 見出しのフォントサイズを調整 */
            h1 {
                font-size: 16pt;  /* より控えめなサイズに */
                margin-top: 0.8em;
                margin-bottom: 0.5em;
                line-height: 1.2;
            }

            h2 {
                font-size: 14pt;  /* Level 2相当のサイズ */
                margin-top: 0.7em;
                margin-bottom: 0.4em;
                line-height: 1.2;
            }

            h3 {
                font-size: 12pt;
                margin-top: 0.6em;
                margin-bottom: 0.3em;
                line-height: 1.2;
            }

            h4, h5, h6 {
                font-size: 11pt;
                margin-top: 0.5em;
                margin-bottom: 0.3em;
                line-height: 1.2;
            }

            /* 段落の行間を調整 */
            p {
                margin-top: 0.4em;
                margin-bottom: 0.4em;
                line-height: 1.4;  /* 行間を狭く */
            }

            /* ページ区切り制御 */
            h1, h2, h3 {
                page-break-after: avoid;
            }

            /* Phase 4: 図表の改ページ制御 */
            .embedded-figure {
                page-break-inside: avoid;
                margin: 1.5em 0;
            }

            img {
                page-break-inside: avoid;
            }

            table {
                page-break-inside: avoid;
            }

            /* 改ページマーカーで必ず改ページ（PDF出力時は非表示） */
            .page-break-marker {
                page-break-before: always;
                display: none; /* PDF出力時は完全に非表示 */
                margin: 0;
                height: 0;
            }

            /* 孤立行・未亡人行の防止 */
            p {
                orphans: 3;
                widows: 3;
            }
        """)

        # PDFを生成
        pdf_bytes = io.BytesIO()
        html_obj.write_pdf(pdf_bytes, stylesheets=[pdf_css])

        return pdf_bytes.getvalue()

    def generate_pdf_from_markdown(
        self,
        markdown_text: str,
        layout_metadata: Optional[dict] = None,
        target_language: str = 'ja',
        job_id: Optional[str] = None
    ) -> bytes:
        """
        Markdownから直接PDFを生成

        Args:
            markdown_text: Markdownテキスト
            layout_metadata: レイアウト情報
            target_language: 言語コード
            job_id: ジョブID

        Returns:
            PDFのバイト列
        """
        from app.services.html_generator import HTMLGenerator
        from app.services.document_preprocessor import DocumentPreprocessor

        # PDF用にMarkdownを前処理（ページ番号削除 + 改ページ挿入）
        preprocessor = DocumentPreprocessor()
        pdf_markdown = preprocessor.prepare_for_paged_output(
            markdown_text,
            output_format='pdf'
        )

        # まずHTMLを生成
        html_gen = HTMLGenerator()
        html_content = html_gen.generate_html(
            pdf_markdown,
            layout_metadata,
            target_language,
            job_id
        )

        # Phase 4: PDF生成用に画像URLをファイルパスに変換
        if job_id:
            import re
            from pathlib import Path
            import logging
            logger = logging.getLogger(__name__)

            # uploads/{job_id}/figures/ の構造
            # 絶対パスに変換
            storage_dir = Path("storage").resolve() / "documents" / job_id / "figures"
            logger.info(f"PDF generation: Looking for images in {storage_dir}")

            # /api/figures/{job_id}/... を file:// URLに変換、存在しない場合は削除
            image_count = 0
            found_count = 0
            missing_count = 0

            def replace_img_url(match):
                nonlocal image_count, found_count, missing_count
                image_count += 1
                full_tag = match.group(0)
                logger.debug(f"Processing img tag: {full_tag[:100]}...")
                src_match = re.search(r'src="(/api/figures/[^"]+)"', full_tag)
                if src_match:
                    api_url = src_match.group(1)
                    # /api/figures/{job_id}/figures/page_1_fig_1.png → page_1_fig_1.png
                    filename = api_url.split('/')[-1]
                    file_path = storage_dir / filename
                    logger.info(f"Checking figure: {filename} at {file_path}")
                    if file_path.exists():
                        # file:// URLに変換（絶対パス）
                        file_url = file_path.as_uri()
                        found_count += 1
                        logger.info(f"✓ Image found: {filename} -> {file_url}")
                        return full_tag.replace(api_url, file_url)
                    else:
                        # 画像ファイルが存在しない場合は、imgタグを削除
                        missing_count += 1
                        logger.warning(f"✗ Image NOT found: {filename} (expected at {file_path})")
                        return ''
                # 相対パスも削除
                logger.warning(f"✗ Could not parse image src from: {full_tag}")
                return ''

            # Phase 4: figure要素内のimg要素も処理
            html_content = re.sub(r'<img[^>]+>', replace_img_url, html_content)
            logger.info(f"PDF image processing complete: {image_count} total, {found_count} found, {missing_count} missing")

        # HTMLからPDFを生成
        return self.generate_pdf(html_content)
