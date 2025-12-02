"""
図表統合サービスのテスト
"""
import pytest
from app.services.figure_integrator import FigureIntegrator, IntegratedFigure, PagedFigureData
from app.services.opencv_detector import OpenCVFigure
from app.models.schemas import FigureData, FigurePosition


class TestFigureIntegrator:
    """FigureIntegratorのテストクラス"""

    @pytest.fixture
    def integrator(self):
        """テスト用のIntegratorインスタンス"""
        return FigureIntegrator(position_tolerance=100)

    @pytest.fixture
    def sample_gemini_figures(self):
        """サンプルGemini図表（ページ情報付き）"""
        return [
            PagedFigureData(
                page=1,
                figure=FigureData(
                    id=1,
                    type="diagram",
                    description="Arrow diagram",
                    position=FigurePosition(x=100, y=100, width=200, height=150)
                )
            ),
            PagedFigureData(
                page=1,
                figure=FigureData(
                    id=2,
                    type="table",
                    description="Data table",
                    position=FigurePosition(x=100, y=400, width=300, height=100)
                )
            )
        ]

    @pytest.fixture
    def sample_opencv_figures(self):
        """サンプルOpenCV図表"""
        return [
            OpenCVFigure(
                page=1,
                x=95,  # Gemini図表1に近い位置
                y=95,
                width=210,
                height=160,
                confidence=0.95,
                type="diagram"
            ),
            OpenCVFigure(
                page=1,
                x=105,  # Gemini図表2に近い位置
                y=405,
                width=295,
                height=95,
                confidence=0.92,
                type="table"
            )
        ]

    def test_integrator_initialization(self, integrator):
        """Integratorの初期化テスト"""
        assert integrator.position_tolerance == 100

    def test_integrate_figures_with_matches(
        self,
        integrator,
        sample_gemini_figures,
        sample_opencv_figures
    ):
        """図表統合テスト - マッチング成功"""
        integrated = integrator.integrate_figures(
            sample_gemini_figures,
            sample_opencv_figures,
            fallback_enabled=True
        )

        # 統合結果の検証
        assert len(integrated) == 2

        # 最初の図表（ハイブリッド）
        fig1 = integrated[0]
        assert fig1.id == "1"
        assert fig1.source == "hybrid"
        assert fig1.position.x == 95  # OpenCV座標を採用
        assert fig1.position.y == 95
        assert fig1.description == "Arrow diagram"  # Geminiメタデータを保持

        # 2番目の図表（ハイブリッド）
        fig2 = integrated[1]
        assert fig2.id == "2"
        assert fig2.source == "hybrid"
        assert fig2.position.x == 105
        assert fig2.description == "Data table"

    def test_integrate_figures_with_gemini_fallback(self, integrator):
        """図表統合テスト - Geminiフォールバック"""
        gemini_figures = [
            PagedFigureData(
                page=1,
                figure=FigureData(
                    id=1,
                    type="diagram",
                    description="Test figure",
                    position=FigurePosition(x=100, y=100, width=200, height=150)
                )
            )
        ]

        # OpenCV図表が異なるページにある（マッチング失敗）
        opencv_figures = [
            OpenCVFigure(
                page=2,  # 異なるページ
                x=100,
                y=100,
                width=200,
                height=150,
                confidence=0.95,
                type="diagram"
            )
        ]

        integrated = integrator.integrate_figures(
            gemini_figures,
            opencv_figures,
            fallback_enabled=True
        )

        # Geminiフォールバック + OpenCV追加 = 2図表
        assert len(integrated) == 2

        # Geminiフォールバック図表（ページ1）
        gemini_fallback = next(fig for fig in integrated if fig.page == 1)
        assert gemini_fallback.id == "1"
        assert gemini_fallback.source == "gemini"
        assert gemini_fallback.position.x == 100  # Gemini座標を使用

        # OpenCV追加図表（ページ2）
        opencv_only = next(fig for fig in integrated if fig.page == 2)
        assert opencv_only.source == "opencv"
        assert opencv_only.id.startswith("opencv_")

    def test_integrate_figures_opencv_only(self, integrator):
        """図表統合テスト - OpenCVのみ検出"""
        gemini_figures = []
        opencv_figures = [
            OpenCVFigure(
                page=1,
                x=100,
                y=100,
                width=200,
                height=150,
                confidence=0.95,
                type="diagram"
            )
        ]

        integrated = integrator.integrate_figures(
            gemini_figures,
            opencv_figures,
            fallback_enabled=True
        )

        assert len(integrated) == 1
        assert integrated[0].source == "opencv"
        assert integrated[0].id.startswith("opencv_1_")

    def test_calculate_matching_score(
        self,
        integrator,
        sample_gemini_figures,
        sample_opencv_figures
    ):
        """マッチングスコア計算テスト"""
        gemini_fig = sample_gemini_figures[0].figure
        opencv_fig = sample_opencv_figures[0]

        score = integrator._calculate_matching_score(gemini_fig, opencv_fig)

        # 近い位置、似たサイズ、同じタイプ → 高スコア
        assert score > 0.7

    def test_convert_to_figure_data(self, integrator):
        """IntegratedFigure → FigureData変換テスト"""
        integrated = [
            IntegratedFigure(
                id="1",
                page=1,
                position=FigurePosition(x=100, y=100, width=200, height=150),
                type="diagram",
                description="Test",
                confidence=0.9,
                source="hybrid"
            )
        ]

        figure_data_list = integrator.convert_to_figure_data(integrated)

        assert len(figure_data_list) == 1
        assert isinstance(figure_data_list[0], FigureData)
        assert figure_data_list[0].id == 1  # intに変換される
        assert figure_data_list[0].type == "diagram"

    def test_integrate_figures_multiple_pages(self, integrator):
        """複数ページの図表統合テスト"""
        gemini_figures = [
            PagedFigureData(
                page=1,
                figure=FigureData(
                    id=1,
                    type="diagram",
                    description="Page 1 figure",
                    position=FigurePosition(x=100, y=100, width=200, height=150)
                )
            ),
            PagedFigureData(
                page=2,
                figure=FigureData(
                    id=2,
                    type="table",
                    description="Page 2 table",
                    position=FigurePosition(x=100, y=100, width=300, height=100)
                )
            )
        ]

        opencv_figures = [
            OpenCVFigure(page=1, x=95, y=95, width=210, height=160, confidence=0.95, type="diagram"),
            OpenCVFigure(page=2, x=105, y=105, width=295, height=95, confidence=0.92, type="table")
        ]

        integrated = integrator.integrate_figures(
            gemini_figures,
            opencv_figures,
            fallback_enabled=True
        )

        assert len(integrated) == 2
        pages = {fig.page for fig in integrated}
        assert pages == {1, 2}
