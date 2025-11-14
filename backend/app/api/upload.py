"""
PDFアップロードAPI
"""
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from uuid import uuid4
import os
import shutil

from app.config import settings
from app.utils.supabase_client import get_supabase_admin_client
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.ocr_orchestrator import OCROrchestrator
from app.models.schemas import UploadResponse


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    PDFアップロード＆OCR開始

    Args:
        file: PDFファイル

    Returns:
        ジョブID

    Note:
        書字方向（縦書き/横書き）はGeminiが自動判定します
    """

    # ファイルタイプ確認
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # ファイルサイズ確認
    file.file.seek(0, 2)  # ファイルの最後に移動
    file_size = file.file.tell()
    file.file.seek(0)  # ファイルの先頭に戻る

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size ({settings.MAX_FILE_SIZE_MB}MB)"
        )

    # ジョブID生成
    job_id = str(uuid4())

    # Supabaseクライアント
    supabase = get_supabase_admin_client()

    # アップロードディレクトリ作成
    upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(upload_dir, exist_ok=True)

    # PDFをローカルに一時保存
    local_pdf_path = os.path.join(upload_dir, "original.pdf")
    with open(local_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Supabase Storageにアップロード
    try:
        with open(local_pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        storage_path = f"{job_id}/original.pdf"
        supabase.storage.from_('pdfs').upload(
            storage_path,
            pdf_bytes,
            {'content-type': 'application/pdf'}
        )

        pdf_url = supabase.storage.from_('pdfs').get_public_url(storage_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")

    # DBにジョブレコード作成
    try:
        supabase.table('translation_jobs').insert({
            'id': job_id,
            'original_filename': file.filename,
            'pdf_url': pdf_url,
            'ocr_status': 'pending'
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job record: {str(e)}")

    # バックグラウンドでOCR開始
    if background_tasks:
        background_tasks.add_task(
            run_ocr_task,
            job_id,
            local_pdf_path
        )

    return UploadResponse(
        job_id=job_id,
        status='pending',
        message='OCR processing started (writing direction will be auto-detected)'
    )


async def run_ocr_task(job_id: str, pdf_path: str):
    """バックグラウンドOCRタスク"""

    supabase = get_supabase_admin_client()

    try:
        # Gemini OCRサービス初期化
        gemini_service = GeminiOCRService(api_key=settings.GEMINI_API_KEY)

        # OCRオーケストレーター初期化
        orchestrator = OCROrchestrator(gemini_service, supabase)

        # OCR実行（書字方向は自動判定）
        markdown_url = await orchestrator.process_pdf(job_id, pdf_path)

        print(f"OCR completed for job {job_id}: {markdown_url}")

    except Exception as e:
        print(f"OCR failed for job {job_id}: {str(e)}")

        # エラー記録
        supabase.table('translation_jobs').update({
            'ocr_status': 'failed',
            'ocr_error': str(e)
        }).eq('id', job_id).execute()
