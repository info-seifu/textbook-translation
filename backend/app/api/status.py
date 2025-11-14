"""
ステータス確認API
"""
from fastapi import APIRouter, HTTPException

from app.utils.supabase_client import get_supabase_admin_client
from app.models.schemas import JobStatusResponse


router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    ジョブステータス取得

    Args:
        job_id: ジョブID

    Returns:
        ジョブ情報と翻訳出力一覧
    """

    supabase = get_supabase_admin_client()

    try:
        # ジョブ情報取得
        job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # 翻訳出力一覧も取得
        outputs = supabase.table('translation_outputs').select('*').eq('job_id', job_id).execute()

        return JobStatusResponse(
            job=job.data,
            translations=outputs.data if outputs.data else []
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get("/outputs/{output_id}")
async def get_output_status(output_id: str):
    """
    翻訳出力ステータス取得

    Args:
        output_id: 翻訳出力ID

    Returns:
        翻訳出力情報
    """

    supabase = get_supabase_admin_client()

    try:
        output = supabase.table('translation_outputs').select('*').eq('id', output_id).single().execute()

        if not output.data:
            raise HTTPException(status_code=404, detail=f"Output {output_id} not found")

        return output.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get output status: {str(e)}")
