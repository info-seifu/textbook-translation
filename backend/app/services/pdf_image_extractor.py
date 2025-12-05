"""
PDF画像抽出サービス

PDFから図表領域を画像として抽出する
"""
import logging
from typing import List, Tuple, Dict, Any
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFImageExtractor:
    """PDFから図表を画像として抽出"""

    def __init__(self, dpi_scale: float = 2.0):
        """
        Args:
            dpi_scale: DPIスケール（デフォルト2.0 = 144 DPI）
        """
        self.dpi_scale = dpi_scale

    def extract_figure_images(
        self,
        pdf_path: str,
        figures: List[Dict[str, Any]],
        output_dir: str,
        margin: int = 20
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        図表領域を画像として抽出

        Args:
            pdf_path: PDFファイルパス
            figures: 図表情報のリスト（page, x, y, width, height を含む辞書）
            output_dir: 出力ディレクトリ
            margin: 抽出時の余白（ピクセル）

        Returns:
            (画像ファイルパス, 図表情報) のタプルのリスト
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pdf_document = fitz.open(pdf_path)
        extracted = []

        try:
            for idx, fig_info in enumerate(figures):
                try:
                    page_num = fig_info['page']
                    page_idx = page_num - 1

                    if page_idx < 0 or page_idx >= pdf_document.page_count:
                        logger.warning(f"Invalid page number: {page_num}")
                        continue

                    page = pdf_document[page_idx]

                    # 座標情報を取得
                    x = fig_info.get('x', 0)
                    y = fig_info.get('y', 0)
                    width = fig_info.get('width', 100)
                    height = fig_info.get('height', 100)

                    # 座標の妥当性チェック
                    if width <= 0 or height <= 0:
                        logger.warning(
                            f"Invalid dimensions for figure on page {page_num}: "
                            f"width={width}, height={height}, skipping"
                        )
                        continue

                    # DPIスケーリングのためのマトリックス
                    mat = fitz.Matrix(self.dpi_scale, self.dpi_scale)

                    # 抽出領域を計算（余白を追加）
                    # 注: 座標はDPIスケール前の値として扱う
                    x0 = max(0, x - margin)
                    y0 = max(0, y - margin)
                    x1 = min(page.rect.width, x + width + margin)
                    y1 = min(page.rect.height, y + height + margin)

                    # 抽出領域の妥当性チェック
                    if x1 <= x0 or y1 <= y0:
                        logger.warning(
                            f"Invalid rect for figure on page {page_num}: "
                            f"rect=({x0}, {y0}, {x1}, {y1}), skipping"
                        )
                        continue

                    rect = fitz.Rect(x0, y0, x1, y1)

                    # 画像を抽出
                    pix = page.get_pixmap(matrix=mat, clip=rect)

                    # ピクセルサイズのチェック
                    if pix.width <= 0 or pix.height <= 0:
                        logger.warning(
                            f"Invalid pixmap size for figure on page {page_num}: "
                            f"{pix.width}x{pix.height}, skipping"
                        )
                        continue

                    # ファイル名生成
                    figure = fig_info.get('figure')
                    if figure and hasattr(figure, 'id'):
                        fig_id = figure.id
                    else:
                        fig_id = f"fig_{idx}"

                    if figure and hasattr(figure, 'type'):
                        fig_type = figure.type
                    else:
                        fig_type = "figure"

                    filename = f"page{page_num}_{fig_type}_{fig_id}.png"
                    file_path = output_path / filename

                    # 画像保存
                    pix.save(str(file_path))
                    extracted.append((str(file_path), fig_info))

                    logger.debug(
                        f"Extracted: {filename} "
                        f"({pix.width}x{pix.height}px from page {page_num})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to extract figure {idx} from page {fig_info.get('page', '?')}: {e}"
                    )

        finally:
            pdf_document.close()

        logger.info(f"Extracted {len(extracted)} figure images")
        return extracted

    def extract_page_region(
        self,
        pdf_path: str,
        page_num: int,
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: str
    ) -> bool:
        """
        特定ページの指定領域を画像として抽出

        Args:
            pdf_path: PDFファイルパス
            page_num: ページ番号（1始まり）
            x: X座標
            y: Y座標
            width: 幅
            height: 高さ
            output_path: 出力画像パス

        Returns:
            成功時True
        """
        try:
            pdf_document = fitz.open(pdf_path)
            page_idx = page_num - 1

            if page_idx < 0 or page_idx >= pdf_document.page_count:
                logger.error(f"Invalid page number: {page_num}")
                return False

            page = pdf_document[page_idx]

            # DPIスケーリング
            mat = fitz.Matrix(self.dpi_scale, self.dpi_scale)

            # 抽出領域
            rect = fitz.Rect(x, y, x + width, y + height)

            # 画像抽出
            pix = page.get_pixmap(matrix=mat, clip=rect)

            # 保存
            pix.save(output_path)

            pdf_document.close()
            return True

        except Exception as e:
            logger.error(f"Failed to extract region: {e}")
            return False
