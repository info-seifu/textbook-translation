"""
HTML生成サービス
Markdownをレイアウト付きHTMLに変換
"""
import markdown
from typing import Optional, Dict, Any
import re


class HTMLGenerator:
    """Markdownをレイアウト付きHTMLに変換"""

    def generate_html(
        self,
        markdown_text: str,
        layout_metadata: Optional[Dict[str, Any]] = None,
        target_language: str = 'ja',
        job_id: Optional[str] = None
    ) -> str:
        """
        Markdownをレイアウト付きHTMLに変換

        Args:
            markdown_text: Markdownテキスト
            layout_metadata: OCRで取得したレイアウト情報
            target_language: 言語コード
            job_id: ジョブID（図解パス解決用）

        Returns:
            HTML文字列
        """

        # レイアウト情報を解析
        writing_mode = self._detect_writing_mode(layout_metadata)
        columns = self._detect_columns(layout_metadata)

        # MarkdownをHTMLに変換
        html_content = markdown.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'tables']
        )

        # 図解パスを調整（ローカルパスに対応）
        if job_id:
            html_content = self._adjust_image_paths(html_content, job_id)

        # CSSスタイルを生成
        css = self._generate_css(writing_mode, columns, target_language)

        # 完全なHTMLを構築
        full_html = self._build_full_html(
            html_content,
            css,
            writing_mode,
            target_language
        )

        return full_html

    def _detect_writing_mode(
        self,
        layout_metadata: Optional[Dict[str, Any]]
    ) -> str:
        """
        書字方向を検出

        Returns:
            'vertical' or 'horizontal'
        """
        if not layout_metadata:
            return 'horizontal'

        # レイアウトメタデータから書字方向を取得
        pages = layout_metadata.get('pages', [])
        if not pages:
            return 'horizontal'

        # 最初のページの書字方向を基準とする
        first_page = pages[0]
        detected_mode = first_page.get('detected_writing_mode', 'horizontal')

        # vertical, horizontal, mixed のいずれか
        if detected_mode == 'vertical':
            return 'vertical'
        else:
            # horizontal または mixedの場合は横書き扱い
            return 'horizontal'

    def _detect_columns(self, layout_metadata: Optional[Dict[str, Any]]) -> int:
        """
        段組み数を検出

        Returns:
            段組み数（1, 2, 3など）
        """
        if not layout_metadata:
            return 1

        pages = layout_metadata.get('pages', [])
        if not pages:
            return 1

        # 最初のページのレイアウト情報から段組み数を取得
        first_page = pages[0]
        layout_info = first_page.get('layout_info', {})
        return layout_info.get('columns', 1)

    def _adjust_image_paths(self, html_content: str, job_id: str) -> str:
        """
        図解のパスをローカルストレージのパスに調整し、figure要素で囲む（Phase 3）

        Args:
            html_content: HTML文字列
            job_id: ジョブID

        Returns:
            パス調整済みHTML
        """
        # Phase 3: 画像をfigure要素で囲む
        # 例: <img alt="図1" src="figures/page_1_fig_1.png" />
        # -> <figure class="embedded-figure">
        #      <img src="/api/figures/{job_id}/figures/page_1_fig_1.png" alt="図1">
        #      <figcaption>図1</figcaption>
        #    </figure>
        pattern = r'<img alt="([^"]*)" src="(figures/[^"]+)" ?/?>'

        def replace_with_figure(match):
            alt_text = match.group(1)
            rel_path = match.group(2)
            # APIパスに変換
            full_path = f"/api/figures/{job_id}/{rel_path}"

            # figure要素で囲む
            return (
                f'<figure class="embedded-figure">\n'
                f'  <img src="{full_path}" alt="{alt_text}">\n'
                f'  <figcaption>{alt_text}</figcaption>\n'
                f'</figure>'
            )

        return re.sub(pattern, replace_with_figure, html_content)

    def _generate_css(
        self,
        writing_mode: str,
        columns: int,
        target_language: str
    ) -> str:
        """
        レイアウトに応じたCSSを生成

        Args:
            writing_mode: 書字方向
            columns: 段組み数
            target_language: 言語コード

        Returns:
            CSS文字列
        """

        # 基本スタイル
        base_css = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Noto Sans JP', 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif;
            line-height: 1.8;
            color: #333;
            background: #fff;
            padding: 20mm;
        }

        .page {
            max-width: 210mm;
            min-height: 297mm;
            margin: 0 auto;
            background: white;
            padding: 20mm;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }

        h1, h2, h3, h4, h5, h6 {
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: bold;
        }

        h1 { font-size: 2em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.3em; }

        p {
            margin-bottom: 1em;
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
        }

        /* Phase 3: 図表配置 */
        .embedded-figure {
            margin: 2rem 0;
            text-align: center;
            page-break-inside: avoid;
        }

        .embedded-figure img {
            max-width: 100%;
            height: auto;
            margin: 0 auto 0.5rem;
        }

        .embedded-figure figcaption {
            font-size: 0.9em;
            color: #666;
            font-style: italic;
            margin-top: 0.5rem;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }

        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }

        pre {
            background-color: #f4f4f4;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1em 0;
        }

        blockquote {
            border-left: 4px solid #ddd;
            padding-left: 1em;
            margin: 1em 0;
            color: #666;
        }
        """

        # 縦書き対応
        if writing_mode == 'vertical':
            writing_mode_css = """
        .content {
            writing-mode: vertical-rl;
            text-orientation: upright;
        }
            """
        else:
            writing_mode_css = ""

        # 段組み対応
        if columns > 1:
            column_css = f"""
        .content {{
            column-count: {columns};
            column-gap: 2em;
            column-rule: 1px solid #ddd;
        }}
            """
        else:
            column_css = ""

        # 言語別フォント調整
        if target_language in ['zh', 'zh-CN']:
            font_css = """
        body {
            font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
        }
            """
        elif target_language in ['zh-TW', 'zh-HK']:
            font_css = """
        body {
            font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
        }
            """
        elif target_language == 'ko':
            font_css = """
        body {
            font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        }
            """
        else:
            font_css = ""

        # 印刷用CSS（Phase 3: 改ページ制御を追加）
        print_css = """
        @media print {
            body {
                padding: 0;
            }
            .page {
                box-shadow: none;
                padding: 0;
                margin: 0;
            }
            @page {
                size: A4;
                margin: 20mm;
            }

            /* Phase 3: セクション単位での改ページ制御 */
            h1[id^="page-"] {
                page-break-before: auto;
            }

            /* 図表が分割されないようにする */
            .embedded-figure {
                page-break-inside: avoid;
            }

            /* 大きな見出しの後に改ページが来ないようにする */
            h1, h2, h3 {
                page-break-after: avoid;
            }
        }
        """

        return base_css + writing_mode_css + column_css + font_css + print_css

    def _build_full_html(
        self,
        content: str,
        css: str,
        writing_mode: str,
        language: str
    ) -> str:
        """
        完全なHTML文書を構築

        Args:
            content: HTML本文
            css: CSS文字列
            writing_mode: 書字方向
            language: 言語コード

        Returns:
            完全なHTML文書
        """

        return f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>翻訳済み教科書</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="page">
        <div class="content">
{content}
        </div>
    </div>
</body>
</html>"""
