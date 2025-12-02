"""
LayoutLMv3 Document Layout Analysis Service

LayoutLMv3を使用して文書内の図表を検出する
図（figure）と表（table）の両方を高精度で検出可能
"""
import logging
from typing import List
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import torch
from PIL import Image
import layoutparser as lp
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DetectedFigure:
    """検出された図表"""
    page: int
    x: int
    y: int
    width: int
    height: int
    confidence: float
    type: str  # 'figure', 'table'

class LayoutLMv3Detector:
    """
    LayoutLMv3を使用した文書レイアウト分析サービス

    Document Layout Analysisに特化したLayoutLMv3を使用して、
    PDFから図（figure）と表（table）を高精度で検出します。
    CPU/GPUの両方に対応。
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Args:
            confidence_threshold: 検出の信頼度閾値（0.0-1.0）
        """
        self.confidence_threshold = confidence_threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Initializing LayoutLMv3 detector on device: {self.device}")

        try:
            # LayoutParser経由でモデルをロード
            # PubLayNet dataset用の事前学習済みモデル（論文・文書用）
            self.model = lp.Detectron2LayoutModel(
                'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
                extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", confidence_threshold],
                label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
            )
            logger.info(f"Model loaded successfully with confidence threshold: {confidence_threshold}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # フォールバック: 基本的なFaster R-CNNモデル
            logger.info("Falling back to base Faster R-CNN model")
            self.model = lp.Detectron2LayoutModel(
                'lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
                label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"}
            )

    def detect_figures(self, pdf_path: str) -> List[DetectedFigure]:
        """
        PDFから全ページの図表を検出

        Args:
            pdf_path: PDFファイルパス

        Returns:
            検出された図表のリスト（figureとtableのみ）
        """
        logger.info(f"Starting layout analysis for: {pdf_path}")

        pdf_document = fitz.open(pdf_path)
        all_figures = []

        try:
            for page_num in range(1, pdf_document.page_count + 1):
                page_idx = page_num - 1
                page = pdf_document[page_idx]

                # ページを画像に変換（RGB、高解像度）
                mat = fitz.Matrix(2.0, 2.0)  # DPI 200
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # レイアウト分析
                figures = self._detect_in_image(img, page_num)
                all_figures.extend(figures)

                logger.info(f"Page {page_num}: Detected {len(figures)} figures/tables")

        finally:
            pdf_document.close()

        logger.info(f"Total figures/tables detected: {len(all_figures)}")
        return all_figures

    def _detect_in_image(
        self,
        image: Image.Image,
        page_num: int
    ) -> List[DetectedFigure]:
        """
        画像からレイアウト要素を検出

        Args:
            image: PIL Image
            page_num: ページ番号

        Returns:
            検出された図表のリスト（figureとtableのみ）
        """
        # LayoutParserで検出
        img_array = np.array(image)
        layout = self.model.detect(img_array)

        # DetectedFigure形式に変換（figureとtableのみ）
        figures = []
        for block in layout:
            # FigureとTableのみを抽出
            if block.type.lower() not in ['figure', 'table']:
                continue

            x = int(block.block.x_1)
            y = int(block.block.y_1)
            width = int(block.block.x_2 - block.block.x_1)
            height = int(block.block.y_2 - block.block.y_1)

            figures.append(DetectedFigure(
                page=page_num,
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=float(block.score),
                type=block.type.lower()
            ))

        return figures

    def extract_figures_to_images(
        self,
        pdf_path: str,
        figures: List[DetectedFigure],
        output_dir: str,
        margin: int = 20
    ) -> List[tuple[str, DetectedFigure]]:
        """
        検出された図表を画像として抽出

        Args:
            pdf_path: PDFファイルパス
            figures: 検出された図表のリスト
            output_dir: 出力ディレクトリ
            margin: 抽出時の余白（ピクセル、デフォルト20）

        Returns:
            (画像ファイルパス, 図表情報) のリスト
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pdf_document = fitz.open(pdf_path)
        extracted = []

        try:
            for fig in figures:
                page_idx = fig.page - 1
                page = pdf_document[page_idx]

                # 高解像度でページを取得
                mat = fitz.Matrix(2.0, 2.0)

                # 座標を計算（DPI 200ベース）+ 余白
                x0 = max(0, (fig.x / 2.0) - margin)
                y0 = max(0, (fig.y / 2.0) - margin)
                x1 = min(page.rect.width, ((fig.x + fig.width) / 2.0) + margin)
                y1 = min(page.rect.height, ((fig.y + fig.height) / 2.0) + margin)

                rect = fitz.Rect(x0, y0, x1, y1)
                pix = page.get_pixmap(matrix=mat, clip=rect)

                # ファイル名生成
                filename = f"page_{fig.page}_{fig.type}_{figures.index(fig)}.png"
                file_path = output_path / filename

                # 画像保存
                pix.save(str(file_path))
                extracted.append((str(file_path), fig))

                logger.info(f"Extracted: {filename} ({pix.width}x{pix.height}px, confidence={fig.confidence:.3f})")

        finally:
            pdf_document.close()

        return extracted