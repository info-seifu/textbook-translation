"""
図表統合サービス

Gemini OCRとLayoutLMv3検出結果を統合してハイブリッド検出を実現。
LayoutLMv3の正確な境界座標とGeminiの意味情報を組み合わせる。
"""

import logging
from typing import List
from dataclasses import dataclass

from app.models.schemas import FigureData, FigurePosition
from app.services.layoutlmv3_detector import DetectedFigure

logger = logging.getLogger(__name__)


@dataclass
class PagedFigureData:
    """ページ番号付きのFigureData"""
    page: int
    figure: FigureData


@dataclass
class IntegratedFigure:
    """統合された図表データ"""
    id: str
    page: int
    position: FigurePosition  # LayoutLMv3座標を優先
    type: str
    description: str  # Geminiメタデータ
    confidence: float
    source: str  # 'layoutlmv3', 'gemini', or 'hybrid'


class FigureIntegrator:
    """Gemini OCRとLayoutLMv3検出結果を統合"""

    def __init__(self, position_tolerance: int = 100):
        """
        Args:
            position_tolerance: 位置の許容誤差（ピクセル）
        """
        self.position_tolerance = position_tolerance

    def _convert_layoutlmv3_type(self, layoutlmv3_type: str) -> str:
        """
        LayoutLMv3の検出タイプをFigureDataの期待する形式に変換

        Args:
            layoutlmv3_type: LayoutLMv3の検出タイプ ('Figure' or 'Table')

        Returns:
            FigureDataの期待する形式のタイプ
        """
        type_mapping = {
            'Figure': 'diagram',  # Figureは一般的に図表なのでdiagramにマッピング
            'Table': 'table',
            'Text': 'diagram',  # Textが誤検出された場合はdiagramにフォールバック
            'Title': 'diagram',
            'List': 'diagram'
        }
        return type_mapping.get(layoutlmv3_type, 'diagram')  # デフォルトはdiagram

    def integrate_figures(
        self,
        gemini_figures: List[PagedFigureData],
        detector_figures: List[DetectedFigure],
        fallback_enabled: bool = True
    ) -> List[IntegratedFigure]:
        """
        GeminiとLayoutLMv3の結果を統合

        Args:
            gemini_figures: Gemini OCRで検出された図表（ページ情報付き）
            detector_figures: LayoutLMv3で検出された図表
            fallback_enabled: LayoutLMv3失敗時のGeminiフォールバック有効化

        Returns:
            統合された図表のリスト
        """
        integrated = []

        # 全ページを処理
        pages = set()
        for fig in gemini_figures:
            pages.add(fig.page)
        for fig in detector_figures:
            pages.add(fig.page)

        for page_num in sorted(pages):
            page_gemini = [f for f in gemini_figures if f.page == page_num]
            page_detector = [f for f in detector_figures if f.page == page_num]

            # ページ内で統合
            page_integrated = self._integrate_page_figures(
                page_gemini,
                page_detector,
                page_num,
                fallback_enabled
            )
            integrated.extend(page_integrated)

        logger.info(
            f"Figure integration completed: "
            f"{len(integrated)} figures "
            f"(Gemini: {len(gemini_figures)}, LayoutLMv3: {len(detector_figures)})"
        )

        return integrated

    def _integrate_page_figures(
        self,
        gemini_figures: List[PagedFigureData],
        detector_figures: List[DetectedFigure],
        page_num: int,
        fallback_enabled: bool
    ) -> List[IntegratedFigure]:
        """
        1ページ内の図表を統合

        戦略: LayoutLMv3座標を優先し、Geminiはメタデータ補完とフォールバックのみ使用
        1. LayoutLMv3図表を先に処理し、近い位置のGeminiメタデータをマッピング
        2. LayoutLMv3にマッチしないGemini図表は、LayoutLMv3が何も検出していない場合のみフォールバック
        3. LayoutLMv3が検出できた場合、Geminiの不正確な座標は使用しない

        Args:
            gemini_figures: Geminiの図表（ページ情報付き）
            detector_figures: LayoutLMv3の図表
            page_num: ページ番号
            fallback_enabled: フォールバック有効化

        Returns:
            統合された図表のリスト
        """
        integrated = []
        used_gemini = set()

        # LayoutLMv3が図表を検出している場合は、LayoutLMv3優先戦略を使用
        if detector_figures:
            logger.debug(
                f"Page {page_num}: Using LayoutLMv3-first strategy "
                f"({len(detector_figures)} LayoutLMv3 figures detected)"
            )

            # LayoutLMv3図表ごとに最適なGeminiメタデータを探してマッピング
            for idx, detector_fig in enumerate(detector_figures):
                best_match = None
                best_score = 0

                # 各Gemini図表とのマッチングを評価
                for gemini_idx, paged_fig in enumerate(gemini_figures):
                    if gemini_idx in used_gemini:
                        continue

                    gemini_fig = paged_fig.figure

                    # LayoutLMv3優先戦略では、タイプの一致を必須とする
                    # （異なるタイプをマッチさせると誤った統合になる）
                    if gemini_fig.type != detector_fig.type:
                        logger.debug(
                            f"Page {page_num}: Skipping Gemini {gemini_fig.id} "
                            f"(type={gemini_fig.type}) for LayoutLMv3 figure "
                            f"(type={detector_fig.type}) - type mismatch"
                        )
                        continue

                    # マッチングスコア計算（LayoutLMv3→Gemini方向）
                    score = self._calculate_matching_score(gemini_fig, detector_fig)

                    if score > best_score:
                        best_score = score
                        best_match = (gemini_idx, gemini_fig)

                # マッチしたGeminiメタデータがあれば統合
                if best_match and best_score > 0.3:  # 閾値
                    gemini_idx, gemini_fig = best_match
                    used_gemini.add(gemini_idx)

                    integrated.append(IntegratedFigure(
                        id=f"hybrid_{page_num}_{idx}",
                        page=page_num,
                        position=FigurePosition(
                            x=detector_fig.x,
                            y=detector_fig.y,
                            width=detector_fig.width,
                            height=detector_fig.height
                        ),
                        type=self._convert_layoutlmv3_type(detector_fig.type),  # LayoutLMv3のタイプを変換
                        description=gemini_fig.description,
                        confidence=0.95,  # ハイブリッドは高信頼度
                        source='hybrid'
                    ))

                    logger.debug(
                        f"Page {page_num}: LayoutLMv3 figure {idx} matched with "
                        f"Gemini {gemini_fig.id} (score: {best_score:.2f}), "
                        f"using LayoutLMv3 coordinates"
                    )
                else:
                    # Geminiメタデータが見つからない場合
                    # ただし、Geminiが同じページで少なくとも1つ図表を検出している場合のみ追加
                    # （Geminiが全く検出していないページのLayoutLMv3検出は誤検出の可能性が高い）
                    if gemini_figures:
                        integrated.append(IntegratedFigure(
                            id=f"layoutlmv3_{page_num}_{idx}",
                            page=page_num,
                            position=FigurePosition(
                                x=detector_fig.x,
                                y=detector_fig.y,
                                width=detector_fig.width,
                                height=detector_fig.height
                            ),
                            type=self._convert_layoutlmv3_type(detector_fig.type),  # LayoutLMv3のタイプを変換
                            description="",  # メタデータなし
                            confidence=detector_fig.confidence * 0.9,
                            source='layoutlmv3'
                        ))

                        logger.debug(
                            f"Page {page_num}: LayoutLMv3 figure {idx} (no Gemini metadata), "
                            f"using LayoutLMv3 coordinates"
                        )
                    else:
                        logger.debug(
                            f"Page {page_num}: Skipping LayoutLMv3 figure {idx} "
                            f"(Gemini detected nothing on this page - likely false positive)"
                        )

        # LayoutLMv3が検出していないGemini図表をフォールバックとして追加
        # Gemini検証で後からフィルタリングされるため、ここでは全て追加
        # フォールバック無効化: 不要な図表が多く検出されるため
        if False and fallback_enabled:
            for gemini_idx, paged_fig in enumerate(gemini_figures):
                if gemini_idx not in used_gemini:
                    gemini_fig = paged_fig.figure

                    # LayoutLMv3が検出しなかったGemini図表を追加
                    # （Gemini検証で後から精度チェックされる）
                    integrated.append(IntegratedFigure(
                        id=str(gemini_fig.id),
                        page=page_num,
                        position=gemini_fig.position,
                        type=gemini_fig.type,
                        description=gemini_fig.description,
                        confidence=0.7,  # Geminiのみは低信頼度
                        source='gemini_only'
                    ))

                    logger.info(
                        f"Page {page_num}: Adding Gemini-only figure {gemini_fig.id} "
                        f"(LayoutLMv3 didn't detect, will be verified by Gemini)"
                    )

        return integrated

    def _calculate_matching_score(
        self,
        gemini_fig: FigureData,
        detector_fig: DetectedFigure
    ) -> float:
        """
        Gemini図表とLayoutLMv3図表のマッチングスコアを計算

        Args:
            gemini_fig: Gemini図表（FigureData）
            detector_fig: LayoutLMv3図表

        Returns:
            マッチングスコア（0.0〜1.0）
        """
        gemini_pos = gemini_fig.position

        # 中心点の距離を計算
        gemini_cx = gemini_pos.x + gemini_pos.width / 2
        gemini_cy = gemini_pos.y + gemini_pos.height / 2
        detector_cx = detector_fig.x + detector_fig.width / 2
        detector_cy = detector_fig.y + detector_fig.height / 2

        distance = ((gemini_cx - detector_cx) ** 2 + (gemini_cy - detector_cy) ** 2) ** 0.5

        # 距離に基づくスコア（近いほど高い）
        distance_score = max(0, 1.0 - distance / self.position_tolerance)

        # サイズの類似性
        gemini_area = gemini_pos.width * gemini_pos.height
        detector_area = detector_fig.width * detector_fig.height
        area_ratio = min(gemini_area, detector_area) / max(gemini_area, detector_area)

        # タイプの一致
        type_match = 1.0 if gemini_fig.type == detector_fig.type else 0.5

        # 総合スコア（位置50%、サイズ30%、タイプ20%）
        score = distance_score * 0.5 + area_ratio * 0.3 + type_match * 0.2
        return score
