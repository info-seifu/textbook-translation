"""
文書前処理サービス

PDF/Docx等のページベース出力形式のための共通前処理
"""

import re
import logging

logger = logging.getLogger(__name__)


class DocumentPreprocessor:
    """PDF/Docx等の出力形式のための共通前処理"""

    @staticmethod
    def prepare_for_paged_output(
        markdown_text: str,
        output_format: str = 'pdf'
    ) -> str:
        """
        ページベース出力用にMarkdownを前処理

        Args:
            markdown_text: 元のMarkdownテキスト
            output_format: 出力形式 ('pdf' or 'docx')

        Returns:
            処理済みMarkdownテキスト
        """
        text = markdown_text

        # 1. 元PDFのページ番号見出しを削除
        # 「# Page X」「# ページ X」を削除
        original_count = len(re.findall(r'^# (Page|ページ) \d+$', text, flags=re.MULTILINE))
        text = re.sub(r'^# (Page|ページ) \d+\n', '', text, flags=re.MULTILINE)
        logger.info(f"Removed {original_count} page number headings")

        # 2. 論理的な区切りで改ページマーカーを挿入
        # 出力形式に応じたマーカーを選択
        if output_format == 'pdf':
            # HTML divタグ（WeasyPrintが解釈）
            page_break = '<div style="page-break-before: always;"></div>'
        elif output_format == 'docx':
            # Docx用のマーカー（将来実装時にpython-docxで処理）
            page_break = '<!-- PAGE_BREAK -->'
        else:
            logger.warning(f"Unknown output format: {output_format}, using PDF format")
            page_break = '<div style="page-break-before: always;"></div>'

        # 問題集パターン: Question, Problem, 問題, 練習, Exercise
        # 教科書パターン: Chapter, Part, 第X章, Unit, Lesson
        # これらの主要見出しの前に改ページ
        patterns = [
            r'^(# (?:Question|Problem|問題|練習|Exercise) )',
            r'^(# (?:Chapter|Part|Unit|Lesson) )',
            r'^(# 第\d+章)',
        ]

        break_count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, flags=re.MULTILINE)
            if matches:
                text = re.sub(
                    pattern,
                    f'{page_break}\n\\1',
                    text,
                    flags=re.MULTILINE
                )
                break_count += len(matches)

        logger.info(f"Inserted {break_count} page breaks for {output_format} output")

        return text

    @staticmethod
    def remove_page_numbers_only(markdown_text: str) -> str:
        """
        ページ番号見出しのみを削除（改ページは挿入しない）

        Args:
            markdown_text: 元のMarkdownテキスト

        Returns:
            ページ番号見出しを削除したMarkdownテキスト
        """
        return re.sub(r'^# (Page|ページ) \d+\n', '', markdown_text, flags=re.MULTILINE)
