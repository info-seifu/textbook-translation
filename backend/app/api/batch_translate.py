"""
バッチ翻訳API
複数言語への同時翻訳
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from uuid import uuid4
import asyncio

from app.config import settings
from app.utils.supabase_client import get_supabase_admin_client
from app.services.translation_orchestrator import TranslationOrchestrator
from app.models.schemas import TranslatorEngine, TargetLanguage


router = APIRouter()


class BatchTranslateRequest(BaseModel):
    """バッチ翻訳リクエスト"""
    job_id: str
    target_languages: List[TargetLanguage]
    translator_engine: TranslatorEngine = "claude"


class BatchTranslateResponse(BaseModel):
    """バッチ翻訳レスポンス"""
    batch_id: str
    output_ids: List[str]
    status: str
    message: str


@router.post("/batch-translate", response_model=BatchTranslateResponse)
async def start_batch_translation(
    request: BatchTranslateRequest,
    background_tasks: BackgroundTasks
):
    """
    複数言語への同時翻訳を開始

    Args:
        job_id: OCR完了済みのジョブID
        target_languages: 翻訳先言語のリスト
        translator_engine: 'claude' または 'gemini'

    Returns:
        バッチID と 各翻訳出力ID
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

    # バッチIDの生成
    batch_id = str(uuid4())

    # 各言語の翻訳出力レコードを作成
    output_ids = []

    for language in request.target_languages:
        output_id = str(uuid4())
        output_ids.append(output_id)

        try:
            supabase.table('translation_outputs').insert({
                'id': output_id,
                'job_id': request.job_id,
                'target_language': language,
                'translator_engine': request.translator_engine,
                'status': 'pending'
            }).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create translation output: {str(e)}")

    # バックグラウンドでバッチ翻訳開始
    background_tasks.add_task(
        run_batch_translation_task,
        batch_id,
        request.job_id,
        request.target_languages,
        request.translator_engine,
        output_ids
    )

    return BatchTranslateResponse(
        batch_id=batch_id,
        output_ids=output_ids,
        status='pending',
        message=f'Batch translation started for {len(request.target_languages)} languages'
    )


async def run_batch_translation_task(
    batch_id: str,
    job_id: str,
    target_languages: List[str],
    translator_engine: str,
    output_ids: List[str]
):
    """バックグラウンドバッチ翻訳タスク"""

    supabase = get_supabase_admin_client()

    # 翻訳オーケストレーター初期化
    orchestrator = TranslationOrchestrator(
        claude_api_key=settings.CLAUDE_API_KEY,
        gemini_api_key=settings.GEMINI_API_KEY,
        supabase_client=supabase
    )

    # 並列翻訳タスクを作成
    tasks = []

    for output_id, language in zip(output_ids, target_languages):
        task = translate_single_language(
            orchestrator,
            supabase,
            output_id,
            job_id,
            language,
            translator_engine
        )
        tasks.append(task)

    # すべての翻訳を並列実行
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"Batch translation completed for batch {batch_id}")


async def translate_single_language(
    orchestrator: TranslationOrchestrator,
    supabase,
    output_id: str,
    job_id: str,
    language: str,
    translator_engine: str
):
    """単一言語の翻訳"""

    try:
        # ステータス更新
        supabase.table('translation_outputs').update({
            'status': 'processing'
        }).eq('id', output_id).execute()

        # 翻訳実行
        import time
        start_time = time.time()

        translated_url = await orchestrator.translate_document(
            job_id,
            language,
            translator_engine
        )

        duration = time.time() - start_time

        # ステータス更新
        supabase.table('translation_outputs').update({
            'status': 'completed',
            'translated_markdown_url': translated_url,
            'translation_duration_seconds': duration
        }).eq('id', output_id).execute()

        print(f"Translation completed for language {language}: {translated_url}")

    except Exception as e:
        print(f"Translation failed for language {language}: {str(e)}")

        # エラー記録
        supabase.table('translation_outputs').update({
            'status': 'failed',
            'error_message': str(e)
        }).eq('id', output_id).execute()


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """
    バッチ翻訳のステータス取得
    （実際にはバッチIDで紐づけていないので、output_idsから取得する必要があります）

    Note: 現在の実装ではバッチIDとoutput_idsの紐付けがないため、
    個別にoutput_idで確認する必要があります
    """
    return {
        "batch_id": batch_id,
        "message": "Please check individual output_ids for status"
    }
