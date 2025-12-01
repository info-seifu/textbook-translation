"""
PDF画像抽出サービス

PDFから図表を画像として抽出し、ファイルシステムに保存する。
Phase 1: レイアウト保持型翻訳機能
"""
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


class PDFImageExtractor:
    """PDFから図表画像を抽出するサービス"""

    def __init__(self):
        """初期化"""
        pass

    def extract_figures_from_pdf(
        self,
        pdf_path: str,
        figures_metadata: List[Dict],
        output_dir: str
    ) -> List[Dict]:
        """
        PDFから図表を画像として抽出

        Args:
            pdf_path: 元PDFのパス
            figures_metadata: OCR結果から得た図表の座標情報
                [
                    {
                        "page": 1,
                        "id": 1,
                        "position": {"x": 100, "y": 200, "width": 300, "height": 400},
                        "type": "diagram",
                        "description": "システム構成図"
                    }
                ]
            output_dir: 画像保存先ディレクトリ

        Returns:
            保存した画像ファイルの情報リスト
            [
                {
                    "id": "page_1_fig_1",
                    "page": 1,
                    "bbox": [100, 200, 400, 600],
                    "normalized_bbox": [0.1, 0.2, 0.4, 0.6],
                    "type": "diagram",
                    "caption": "システム構成図",
                    "file_path": "figures/page_1_fig_1.png"
                }
            ]
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        extracted_figures = []

        try:
            # PDFを開く
            pdf_document = fitz.open(pdf_path)
            logger.info(f"Opened PDF: {pdf_path}, pages: {pdf_document.page_count}")

            for fig_meta in figures_metadata:
                try:
                    page_num = fig_meta.get("page", 1)
                    fig_id = fig_meta.get("id", 0)
                    position = fig_meta.get("position", {})
                    fig_type = fig_meta.get("type", "unknown")
                    description = fig_meta.get("description", "")

                    # ページ番号は1-indexedだが、PyMuPDFは0-indexed
                    page_index = page_num - 1
                    if page_index < 0 or page_index >= pdf_document.page_count:
                        logger.warning(f"Invalid page number: {page_num}")
                        continue

                    page = pdf_document[page_index]
                    page_width = page.rect.width
                    page_height = page.rect.height

                    # 座標を取得（左上原点のピクセル座標）
                    x = position.get("x", 0)
                    y = position.get("y", 0)
                    width = position.get("width", 0)
                    height = position.get("height", 0)

                    # デバッグログ：元の座標を記録
                    logger.info(
                        f"[DEBUG] Processing {fig_id} - Original position from metadata: "
                        f"x={x}, y={y}, width={width}, height={height}, "
                        f"type={fig_type}, description='{description[:50] if description else 'N/A'}...'"
                    )

                    # 座標調整前の値を保存（比較用）
                    original_x = x
                    original_y = y
                    original_width = width
                    original_height = height
                    adjustment_applied = False

                    # 座標調整：Geminiが図の境界を見落とすことがあるため
                    # 特にダイアグラムと表は上部・側面が切れやすい

                    # アローダイアグラム・フローチャートの特別処理（Gemini OCR調整と連動）
                    if fig_type == 'diagram' or 'ダイアグラム' in description or 'arrow' in description.lower() or 'figure' in description.lower():
                        logger.info(f"[DEBUG] {fig_id} identified as DIAGRAM/FIGURE")

                        # Gemini OCRですでに大幅調整されている場合（y=0-50の場合）は追加調整不要
                        if y < 50:
                            logger.info(
                                f"[DEBUG] {fig_id}: Already adjusted to top of page (y={y}) by Gemini OCR. "
                                f"Skipping additional adjustment to avoid over-expansion."
                            )
                            # 左右の余白だけ確保
                            horizontal_expansion = 20
                            adjusted_x = max(0, x - horizontal_expansion)
                            adjusted_width = width + (x - adjusted_x) + horizontal_expansion
                            adjusted_width = min(adjusted_width, page_width - adjusted_x)

                            if adjusted_x != x or adjusted_width != width:
                                logger.info(
                                    f"[DEBUG] Horizontal margin adjustment for {fig_id}: "
                                    f"x: {x} -> {adjusted_x}, width: {width} -> {adjusted_width}"
                                )
                                x = adjusted_x
                                width = adjusted_width
                                adjustment_applied = True

                        # Gemini OCRで中程度の調整済み（y=50-200の場合）
                        elif y < 200:
                            logger.info(
                                f"[DEBUG] {fig_id}: Moderately adjusted by Gemini OCR (y={y}). "
                                f"Applying minimal additional margin."
                            )
                            # 小さめの追加余白
                            upward_margin = 50
                            horizontal_margin = 20

                            adjusted_y = max(0, y - upward_margin)
                            adjusted_height = height + (y - adjusted_y) + 30  # 下にも30px
                            adjusted_height = min(adjusted_height, page_height - adjusted_y)

                            adjusted_x = max(0, x - horizontal_margin)
                            adjusted_width = width + (x - adjusted_x) + horizontal_margin
                            adjusted_width = min(adjusted_width, page_width - adjusted_x)

                            logger.info(
                                f"[DEBUG] Margin adjustment for {fig_id}: "
                                f"y: {y} -> {adjusted_y}, height: {height} -> {adjusted_height}, "
                                f"x: {x} -> {adjusted_x}, width: {width} -> {adjusted_width}"
                            )

                            x = adjusted_x
                            y = adjusted_y
                            width = adjusted_width
                            height = adjusted_height
                            adjustment_applied = True

                        # Gemini OCRでまだ不十分な調整（y >= 200の場合）
                        else:
                            logger.warning(
                                f"[DEBUG] {fig_id}: Still at mid-page position (y={y}) after Gemini OCR. "
                                f"Applying EMERGENCY additional expansion."
                            )
                            # さらに積極的な拡張
                            upward_expansion = min(y, 300)  # y座標分または300pxのどちらか小さい方
                            adjusted_y = max(0, y - upward_expansion)
                            adjusted_height = height + (y - adjusted_y) + 100
                            adjusted_height = min(adjusted_height, page_height - adjusted_y)

                            horizontal_expansion = 30
                            adjusted_x = max(0, x - horizontal_expansion)
                            adjusted_width = width + (x - adjusted_x) + horizontal_expansion
                            adjusted_width = min(adjusted_width, page_width - adjusted_x)

                            logger.info(
                                f"[DEBUG] EMERGENCY adjustment for {fig_id}: "
                                f"Original: x={x}, y={y}, w={width}, h={height} | "
                                f"Adjusted: x={adjusted_x}, y={adjusted_y}, w={adjusted_width}, h={adjusted_height} | "
                                f"Expansions: up={upward_expansion}px, down=100px, horizontal={horizontal_expansion}px"
                            )

                            x = adjusted_x
                            y = adjusted_y
                            width = adjusted_width
                            height = adjusted_height
                            adjustment_applied = True

                    # 表（table）の特別処理
                    elif fig_type == 'table' and y > 300:
                        logger.info(f"[DEBUG] {fig_id} identified as TABLE with y={y} > 300 - applying table adjustment")
                        table_expansion = 100  # 表の場合は100ピクセル拡張（50から増加）
                        adjusted_y = max(0, y - table_expansion)
                        adjusted_height = height + (y - adjusted_y) + 30  # 下にも30px追加
                        adjusted_height = min(adjusted_height, page_height - adjusted_y)

                        logger.info(
                            f"[DEBUG] Table adjustment for {fig_id}: "
                            f"y: {y} -> {adjusted_y}, height: {height} -> {adjusted_height}"
                        )

                        y = adjusted_y
                        height = adjusted_height
                        adjustment_applied = True
                    else:
                        logger.info(f"[DEBUG] {fig_id} - No adjustment needed (type={fig_type}, y={y})")

                    # 調整結果の確認ログ
                    if adjustment_applied:
                        logger.info(
                            f"[DEBUG] {fig_id} - COORDINATE ADJUSTMENT SUMMARY: "
                            f"x: {original_x} -> {x} (delta={original_x-x}), "
                            f"y: {original_y} -> {y} (delta={original_y-y}), "
                            f"width: {original_width} -> {width} (delta={width-original_width}), "
                            f"height: {original_height} -> {height} (delta={height-original_height})"
                        )

                    # 座標情報をログ出力
                    logger.debug(
                        f"Processing figure: page={page_num}, fig={fig_id}, "
                        f"type={fig_meta.get('type', 'unknown')}, "
                        f"position=({x}, {y}, {width}, {height})"
                    )

                    # PyMuPDFの座標系（左上原点）に変換
                    # bboxは (x0, y0, x1, y1) の形式
                    bbox = fitz.Rect(x, y, x + width, y + height)

                    # ページの範囲内にクリップ
                    original_bbox = bbox
                    bbox = bbox & page.rect

                    if original_bbox != bbox:
                        logger.warning(
                            f"Bbox clipped to page bounds: "
                            f"original={original_bbox}, clipped={bbox}"
                        )

                    if bbox.is_empty or bbox.width < 10 or bbox.height < 10:
                        logger.warning(
                            f"Invalid bbox for page {page_num}, fig {fig_id}: {bbox} "
                            f"(size: {bbox.width:.0f}x{bbox.height:.0f})"
                        )
                        continue

                    # 画像として抽出（高解像度：300dpi相当）
                    mat = fitz.Matrix(2.0, 2.0)  # 2倍の解像度
                    pix = page.get_pixmap(matrix=mat, clip=bbox)

                    # PIL Imageに変換
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))

                    # ファイル名を生成
                    filename = f"page_{page_num}_fig_{fig_id}.png"
                    file_path = output_path / filename

                    # 画像を保存
                    img.save(str(file_path), "PNG")

                    # 詳細なログ情報
                    logger.info(
                        f"Extracted figure: {filename} - "
                        f"size={pix.width}x{pix.height}px, "
                        f"bbox=({bbox.x0:.0f}, {bbox.y0:.0f}, {bbox.x1:.0f}, {bbox.y1:.0f}), "
                        f"file_size={len(img_data)} bytes"
                    )

                    # デバッグ：特定の図表の抽出結果を詳細に記録
                    if 'page_5' in filename or 'fig_2' in filename:
                        logger.info(
                            f"[DEBUG] SPECIAL ATTENTION - {filename}: "
                            f"Final extraction bbox: x0={bbox.x0:.0f}, y0={bbox.y0:.0f}, "
                            f"x1={bbox.x1:.0f}, y1={bbox.y1:.0f}, "
                            f"size={bbox.x1-bbox.x0:.0f}x{bbox.y1-bbox.y0:.0f}px, "
                            f"adjustment_applied={'YES (aggressive)' if adjustment_applied else 'NO'}"
                        )

                    # 正規化座標を計算（0.0 - 1.0）
                    normalized_bbox = [
                        bbox.x0 / page_width,
                        bbox.y0 / page_height,
                        bbox.x1 / page_width,
                        bbox.y1 / page_height
                    ]

                    # メタデータを作成
                    figure_info = {
                        "id": f"page_{page_num}_fig_{fig_id}",
                        "page": page_num,
                        "bbox": [bbox.x0, bbox.y0, bbox.x1, bbox.y1],
                        "normalized_bbox": normalized_bbox,
                        "type": fig_type,
                        "caption": description,
                        "file_path": f"figures/{filename}"
                    }

                    extracted_figures.append(figure_info)

                except Exception as e:
                    logger.error(
                        f"Failed to extract figure page={page_num}, "
                        f"id={fig_id}: {e}"
                    )
                    continue

            pdf_document.close()
            logger.info(f"Extracted {len(extracted_figures)} figures")

        except Exception as e:
            logger.error(f"Failed to extract figures from PDF: {e}")
            raise

        return extracted_figures

    def normalize_bbox(
        self,
        bbox: List[float],
        page_width: float,
        page_height: float
    ) -> List[float]:
        """
        座標を正規化（相対座標に変換）

        Args:
            bbox: [x0, y0, x1, y1] の絶対座標
            page_width: ページ幅
            page_height: ページ高さ

        Returns:
            [x0, y0, x1, y1] の相対座標（0.0 - 1.0）
        """
        x0, y0, x1, y1 = bbox
        return [
            x0 / page_width,
            y0 / page_height,
            x1 / page_width,
            y1 / page_height
        ]
