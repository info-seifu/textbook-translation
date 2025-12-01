"""
図表画像提供API (Phase 3, Phase 5拡張)

抽出した図表画像をHTMLやPDFで使用できるように配信する
"""
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse
from pathlib import Path as FilePath
import logging
import json
from typing import List, Dict, Any

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
        # uploads/{job_id}/figures/page_1_fig_1.png
        base_path = FilePath("uploads")
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


@router.get(
    "/figures/{job_id}",
    response_model=List[Dict[str, Any]],
    summary="図表一覧を取得",
    description="ジョブの図表メタデータ一覧を取得する（Phase 5）"
)
async def list_figures(
    job_id: str = Path(..., description="ジョブID")
):
    """
    図表一覧を取得（Phase 5）

    Args:
        job_id: ジョブID

    Returns:
        図表メタデータの配列

    Raises:
        HTTPException: メタデータが見つからない場合
    """
    try:
        # uploads/{job_id}/figures/metadata.json を読み込む
        base_path = FilePath("uploads")
        metadata_path = base_path / job_id / "figures" / "metadata.json"

        # パストラバーサル攻撃を防ぐ
        if not str(metadata_path).startswith(str(base_path)):
            logger.warning(f"Path traversal attempt: {metadata_path}")
            raise HTTPException(status_code=400, detail="Invalid path")

        # ファイルの存在確認
        if not metadata_path.exists():
            logger.info(f"No figures found for job {job_id}")
            # 図表がない場合は空配列を返す
            return []

        # メタデータを読み込む
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        figures = metadata.get('figures', [])
        logger.info(f"Found {len(figures)} figures for job {job_id}")
        return figures

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in metadata file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Invalid metadata format"
        )
    except Exception as e:
        logger.error(f"Error listing figures: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list figures: {str(e)}"
        )
