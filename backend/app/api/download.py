"""
ダウンロードAPI
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
import httpx
import io

from app.utils.supabase_client import get_supabase_admin_client


router = APIRouter()


@router.get("/download/{output_id}/markdown")
async def download_markdown(output_id: str):
    """
    翻訳済みマークダウンをダウンロード

    Args:
        output_id: 翻訳出力ID

    Returns:
        マークダウンファイル
    """

    supabase = get_supabase_admin_client()

    try:
        # 翻訳出力情報取得
        output = supabase.table('translation_outputs').select('*').eq('id', output_id).single().execute()

        if not output.data:
            raise HTTPException(status_code=404, detail=f"Output {output_id} not found")

        if output.data['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Translation not completed (status: {output.data['status']})"
            )

        # マークダウンURLを取得
        markdown_url = output.data.get('translated_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Translated markdown not found")

        # Storageからダウンロード
        async with httpx.AsyncClient() as client:
            response = await client.get(markdown_url)
            response.raise_for_status()
            markdown_content = response.content

        # ファイル名生成
        target_language = output.data['target_language']
        filename = f"translated_{target_language}.md"

        return Response(
            content=markdown_content,
            media_type='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download markdown: {str(e)}")


@router.get("/download/job/{job_id}/master")
async def download_master_markdown(job_id: str):
    """
    マスターマークダウン（日本語）をダウンロード

    Args:
        job_id: ジョブID

    Returns:
        マスターマークダウンファイル
    """

    supabase = get_supabase_admin_client()

    try:
        # ジョブ情報取得
        job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.data['ocr_status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"OCR not completed (status: {job.data['ocr_status']})"
            )

        # マスターマークダウンURLを取得
        markdown_url = job.data.get('japanese_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Master markdown not found")

        # Storageからダウンロード
        async with httpx.AsyncClient() as client:
            response = await client.get(markdown_url)
            response.raise_for_status()
            markdown_content = response.content

        filename = "master_ja.md"

        return Response(
            content=markdown_content,
            media_type='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download master markdown: {str(e)}")
