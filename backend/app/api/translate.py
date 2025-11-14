"""
翻訳API
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4

from app.config import settings
from app.utils.supabase_client import get_supabase_admin_client
from app.services.translation_orchestrator import TranslationOrchestrator
from app.models.schemas import TranslateRequest, TranslationStartResponse


router = APIRouter()


@router.post("/translate", response_model=TranslationStartResponse)
async def start_translation(
    request: TranslateRequest,
    background_tasks: BackgroundTasks
):
    """
    翻訳開始

    Args:
        job_id: OCR完了済みのジョブID
        target_language: 翻訳先言語
        translator_engine: 'claude' または 'gemini'

    Returns:
        翻訳出力ID
    """

    supabase = get_supabase_admin_client()

    # ジョブステータス確認
    try:
        job = supabase.table('translation_jobs').select('*').eq('id', request.job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")

        if job.data['ocr_status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"OCR not completed yet (status: {job.data['ocr_status']})"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check job status: {str(e)}")

    # 翻訳出力レコード作成
    output_id = str(uuid4())

    try:
        supabase.table('translation_outputs').insert({
            'id': output_id,
            'job_id': request.job_id,
            'target_language': request.target_language,
            'translator_engine': request.translator_engine,
            'status': 'pending'
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create translation output: {str(e)}")

    # バックグラウンドで翻訳開始
    background_tasks.add_task(
        run_translation_task,
        output_id,
        request.job_id,
        request.target_language,
        request.translator_engine
    )

    return TranslationStartResponse(
        output_id=output_id,
        status='pending',
        message='Translation started'
    )


async def run_translation_task(
    output_id: str,
    job_id: str,
    target_language: str,
    translator_engine: str
):
    """バックグラウンド翻訳タスク"""

    supabase = get_supabase_admin_client()

    try:
        # ステータス更新
        supabase.table('translation_outputs').update({
            'status': 'processing'
        }).eq('id', output_id).execute()

        # 翻訳オーケストレーター初期化
        orchestrator = TranslationOrchestrator(
            claude_api_key=settings.CLAUDE_API_KEY,
            gemini_api_key=settings.GEMINI_API_KEY,
            supabase_client=supabase
        )

        # 翻訳実行
        import time
        start_time = time.time()

        translated_url = await orchestrator.translate_document(
            job_id,
            target_language,
            translator_engine
        )

        duration = time.time() - start_time

        # ステータス更新
        supabase.table('translation_outputs').update({
            'status': 'completed',
            'translated_markdown_url': translated_url,
            'translation_duration_seconds': duration
        }).eq('id', output_id).execute()

        print(f"Translation completed for output {output_id}: {translated_url}")

    except Exception as e:
        print(f"Translation failed for output {output_id}: {str(e)}")

        # エラー記録
        supabase.table('translation_outputs').update({
            'status': 'failed',
            'error_message': str(e)
        }).eq('id', output_id).execute()
