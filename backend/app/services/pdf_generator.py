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

        # 追加のCSS（PDF最適化用）
        pdf_css = CSS(string="""
            @page {
                size: A4;
                margin: 20mm;
            }

            body {
                font-size: 11pt;
            }

            /* ページ区切り制御 */
            h1, h2, h3 {
                page-break-after: avoid;
            }

            img {
                page-break-inside: avoid;
            }

            table {
                page-break-inside: avoid;
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

        # HTMLからPDFを生成
        return self.generate_pdf(html_content)
