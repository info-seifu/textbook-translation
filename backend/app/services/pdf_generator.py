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

        # PDF生成用に画像URLをファイルパスに変換または削除
        if job_id:
            import re
            from pathlib import Path

            # storage/documents/{job_id}/figures/ の構造
            # 絶対パスに変換
            storage_dir = Path("storage").resolve() / "documents" / job_id / "figures"

            # /api/figures/{job_id}/... を file:// URLに変換、存在しない場合は削除
            def replace_img_url(match):
                full_tag = match.group(0)
                src_match = re.search(r'src="(/api/figures/[^"]+)"', full_tag)
                if src_match:
                    api_url = src_match.group(1)
                    # /api/figures/{job_id}/figures/page1_fig1.png → page1_fig1.png
                    filename = api_url.split('/')[-1]
                    file_path = storage_dir / filename
                    if file_path.exists():
                        # file:// URLに変換（絶対パス）
                        file_url = file_path.as_uri()
                        return full_tag.replace(api_url, file_url)
                    else:
                        # 画像ファイルが存在しない場合は、imgタグを削除
                        return ''
                # 相対パスも削除
                return ''

            html_content = re.sub(r'<img[^>]+>', replace_img_url, html_content)

        # HTMLからPDFを生成
        return self.generate_pdf(html_content)
