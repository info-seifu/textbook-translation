"""
図表画像提供API (Phase 3)

抽出した図表画像をHTMLやPDFで使用できるように配信する
"""
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse
from pathlib import Path as FilePath
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/figures/{job_id}/{figure_path:path}",
    response_class=FileResponse,
    summary="図表画像を取得",
    description="抽出された図表画像ファイルを取得する"
)
async def get_figure(
    job_id: str = Path(..., description="ジョブID"),
    figure_path: str = Path(..., description="図表ファイルパス（例: figures/page_1_fig_1.png）")
):
    """
    図表画像を取得

    Args:
        job_id: ジョブID
        figure_path: 図表ファイルのパス

    Returns:
        画像ファイル

    Raises:
        HTTPException: ファイルが存在しない場合
    """
    try:
        # ローカルストレージのパスを構築
        # storage/documents/{job_id}/figures/page_1_fig_1.png
        base_path = FilePath("storage/documents")
        full_path = base_path / job_id / figure_path

        # パストラバーサル攻撃を防ぐ
        if not str(full_path).startswith(str(base_path)):
            logger.warning(f"Path traversal attempt: {full_path}")
            raise HTTPException(status_code=400, detail="Invalid path")

        # ファイルの存在確認
        if not full_path.exists():
            logger.warning(f"Figure not found: {full_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Figure not found: {figure_path}"
            )

        if not full_path.is_file():
            logger.warning(f"Path is not a file: {full_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # 画像ファイルを返す
        logger.info(f"Serving figure: {full_path}")
        return FileResponse(
            path=str(full_path),
            media_type="image/png",
            filename=full_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving figure: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serve figure: {str(e)}"
        )
