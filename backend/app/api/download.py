"""
ダウンロードAPI
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import httpx

from app.utils.supabase_client import get_supabase_admin_client
from app.services.html_generator import HTMLGenerator
from app.services.pdf_generator import PDFGenerator


router = APIRouter()


@router.get("/download/{output_id}/markdown")
async def download_markdown(output_id: str):
    """
    翻訳済みマークダウンをZIP形式でダウンロード（画像含む）

    Args:
        output_id: 翻訳出力ID

    Returns:
        ZIPファイル（マークダウン + figures/）
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

        job_id = output.data['job_id']
        target_language = output.data['target_language']

        # マークダウンURLを取得
        markdown_url = output.data.get('translated_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Translated markdown not found")

        # Storageからダウンロード
        if markdown_url.startswith('file://'):
            # ローカルファイルシステムから読み込み
            import os
            from pathlib import Path
            import zipfile
            import io

            # file:// プレフィックスを削除してパスを取得
            file_path = markdown_url.replace('file://', '', 1)

            # パスの存在確認と読み込み
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Markdown file not found: {file_path}")

            # figuresディレクトリのパスを取得
            job_dir = Path(file_path).parent
            figures_dir = job_dir / 'figures'

            # ZIPファイルをメモリ上に作成
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # マークダウンファイルを追加
                zip_file.write(file_path, f"translated_{target_language}.md")

                # figuresフォルダがあれば、すべての画像を追加
                if figures_dir.exists() and figures_dir.is_dir():
                    for img_file in figures_dir.glob('*.png'):
                        zip_file.write(img_file, f"figures/{img_file.name}")

            zip_buffer.seek(0)
            zip_content = zip_buffer.read()
        else:
            # HTTPからダウンロード (Supabase等) - TODO: 画像も含める必要がある
            async with httpx.AsyncClient() as client:
                response = await client.get(markdown_url)
                response.raise_for_status()
                markdown_content = response.content

            # 簡易実装：MDファイルのみのZIP
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"translated_{target_language}.md", markdown_content)
            zip_buffer.seek(0)
            zip_content = zip_buffer.read()

        # ファイル名生成
        filename = f"translated_{target_language}.zip"

        return Response(
            content=zip_content,
            media_type='application/zip',
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


@router.get("/download/{output_id}/html")
async def download_html(output_id: str):
    """
    翻訳済みHTMLをZIP形式でダウンロード（画像含む）

    Args:
        output_id: 翻訳出力ID

    Returns:
        ZIPファイル（HTML + figures/）
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

        job_id = output.data['job_id']
        target_language = output.data['target_language']

        # ジョブ情報を取得（レイアウトメタデータ取得のため）
        job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        layout_metadata = job.data.get('layout_metadata')

        # マークダウンURLを取得
        markdown_url = output.data.get('translated_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Translated markdown not found")

        # Storageからマークダウンをダウンロード
        if markdown_url.startswith('file://'):
            # ローカルファイルシステムから読み込み
            import os
            from pathlib import Path
            import zipfile
            import io
            import re

            # file:// プレフィックスを削除してパスを取得
            file_path = markdown_url.replace('file://', '', 1)

            # パスの存在確認と読み込み
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Markdown file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()

            # HTMLを生成（job_id指定でAPIパスになる）
            html_generator = HTMLGenerator()
            html_content = html_generator.generate_html(
                markdown_text,
                layout_metadata,
                target_language,
                job_id
            )

            # 画像パスを相対パスに変換（/api/figures/{job_id}/figures/xxx.png -> figures/xxx.png）
            html_content = re.sub(
                rf'/api/figures/{job_id}/figures/([^"]+)',
                r'figures/\1',
                html_content
            )

            # figuresディレクトリのパスを取得
            job_dir = Path(file_path).parent
            figures_dir = job_dir / 'figures'

            # ZIPファイルをメモリ上に作成
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # HTMLファイルを追加
                zip_file.writestr(f"translated_{target_language}.html", html_content.encode('utf-8'))

                # figuresフォルダがあれば、すべての画像を追加
                if figures_dir.exists() and figures_dir.is_dir():
                    for img_file in figures_dir.glob('*.png'):
                        zip_file.write(img_file, f"figures/{img_file.name}")

            zip_buffer.seek(0)
            zip_content = zip_buffer.read()
        else:
            # HTTPからダウンロード (Supabase等)
            async with httpx.AsyncClient() as client:
                response = await client.get(markdown_url)
                response.raise_for_status()
                markdown_text = response.text

            # HTMLを生成
            html_generator = HTMLGenerator()
            html_content = html_generator.generate_html(
                markdown_text,
                layout_metadata,
                target_language,
                job_id
            )

            # 簡易実装：HTMLファイルのみのZIP（TODO: 画像も含める）
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr(f"translated_{target_language}.html", html_content.encode('utf-8'))
            zip_buffer.seek(0)
            zip_content = zip_buffer.read()

        # ファイル名生成
        filename = f"translated_{target_language}.zip"

        return Response(
            content=zip_content,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download HTML: {str(e)}")


@router.get("/download/{output_id}/pdf")
async def download_pdf(output_id: str):
    """
    翻訳済みPDFをダウンロード

    Args:
        output_id: 翻訳出力ID

    Returns:
        レイアウト付きPDFファイル
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

        job_id = output.data['job_id']
        target_language = output.data['target_language']

        # ジョブ情報を取得（レイアウトメタデータ取得のため）
        job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        layout_metadata = job.data.get('layout_metadata')

        # マークダウンURLを取得
        markdown_url = output.data.get('translated_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Translated markdown not found")

        # Storageからマークダウンをダウンロード
        if markdown_url.startswith('file://'):
            # ローカルファイルシステムから読み込み
            import os

            # file:// プレフィックスを削除してパスを取得
            file_path = markdown_url.replace('file://', '', 1)

            # パスの存在確認と読み込み
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Markdown file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
        else:
            # HTTPからダウンロード (Supabase等)
            async with httpx.AsyncClient() as client:
                response = await client.get(markdown_url)
                response.raise_for_status()
                markdown_text = response.text

        # PDFを生成
        pdf_generator = PDFGenerator()
        pdf_content = pdf_generator.generate_pdf_from_markdown(
            markdown_text,
            layout_metadata,
            target_language,
            job_id
        )

        # ファイル名生成
        filename = f"translated_{target_language}.pdf"

        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")


@router.get("/download/{output_id}/docx")
async def download_docx(output_id: str):
    """
    翻訳済みDocxをダウンロード

    Args:
        output_id: 翻訳出力ID

    Returns:
        編集可能なDocxファイル
    """
    from app.services.docx_generator import DocxGenerator

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

        job_id = output.data['job_id']
        target_language = output.data['target_language']

        # ジョブ情報を取得（レイアウトメタデータ取得のため）
        job = supabase.table('translation_jobs').select('*').eq('id', job_id).single().execute()

        if not job.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        layout_metadata = job.data.get('layout_metadata')

        # マークダウンURLを取得
        markdown_url = output.data.get('translated_markdown_url')

        if not markdown_url:
            raise HTTPException(status_code=404, detail="Translated markdown not found")

        # Storageからマークダウンをダウンロード
        if markdown_url.startswith('file://'):
            # ローカルファイルシステムから読み込み
            import os

            # file:// プレフィックスを削除してパスを取得
            file_path = markdown_url.replace('file://', '', 1)

            # パスの存在確認と読み込み
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Markdown file not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()
        else:
            # HTTPからダウンロード (Supabase等)
            async with httpx.AsyncClient() as client:
                response = await client.get(markdown_url)
                response.raise_for_status()
                markdown_text = response.text

        # Docxを生成
        docx_generator = DocxGenerator()
        docx_content = docx_generator.generate_docx_from_markdown(
            markdown_text,
            layout_metadata,
            target_language,
            job_id
        )

        # ファイル名生成
        filename = f"translated_{target_language}.docx"

        return Response(
            content=docx_content,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to download Docx: {str(e)}")
