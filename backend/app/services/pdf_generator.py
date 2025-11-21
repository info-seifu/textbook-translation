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
                font-size: 11pt;
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

        # まずHTMLを生成
        html_gen = HTMLGenerator()
        html_content = html_gen.generate_html(
            markdown_text,
            layout_metadata,
            target_language,
            job_id
        )

        # Phase 4: PDF生成用に画像URLをファイルパスに変換
        if job_id:
            import re
            from pathlib import Path

            # uploads/{job_id}/figures/ の構造
            # 絶対パスに変換
            storage_dir = Path("uploads").resolve() / job_id / "figures"

            # デバッグ: ディレクトリの存在確認
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"PDF generation: Looking for figures in {storage_dir}")
            if storage_dir.exists():
                files = list(storage_dir.glob("*.png"))
                logger.info(f"Found {len(files)} PNG files: {[f.name for f in files]}")
            else:
                logger.warning(f"Figures directory does not exist: {storage_dir}")

            # Phase 4: /api/figures/{job_id}/... を file:// URLに変換
            def replace_img_url(match):
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
                        logger.info(f"Figure found, converting to: {file_url}")
                        result = full_tag.replace(api_url, file_url)
                        logger.debug(f"Replaced tag: {result[:100]}...")
                        return result
                    else:
                        # 画像ファイルが存在しない場合
                        logger.warning(f"Image not found: {file_path}")
                        return ''
                # 相対パスも処理
                logger.debug(f"No API URL found in tag: {full_tag[:100]}...")
                return full_tag

            # Phase 4: figure要素内のimg要素も処理
            html_content = re.sub(r'<img[^>]+>', replace_img_url, html_content)
            logger.info("PDF generation: Image URL replacement completed")

        # HTMLからPDFを生成
        return self.generate_pdf(html_content)
