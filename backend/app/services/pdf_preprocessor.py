"""
PDF前処理サービス
"""
from pdf2image import convert_from_path
import io
from typing import List


def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[bytes]:
    """
    PDFを高解像度画像に変換

    Args:
        pdf_path: PDFファイルパス
        dpi: 解像度（デフォルト300dpi）

    Returns:
        各ページの画像データ（PNG形式バイト列）のリスト
    """
    try:
        # PDFを画像に変換
        images = convert_from_path(pdf_path, dpi=dpi)

        image_bytes_list = []
        for img in images:
            # PNG形式でバイト列化
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            image_bytes_list.append(img_bytes.getvalue())

        return image_bytes_list

    except Exception as e:
        raise Exception(f"PDF conversion failed: {str(e)}")


def pdf_to_images_from_bytes(pdf_bytes: bytes, dpi: int = 300) -> List[bytes]:
    """
    PDFバイト列を高解像度画像に変換

    Args:
        pdf_bytes: PDFファイルのバイト列
        dpi: 解像度（デフォルト300dpi）

    Returns:
        各ページの画像データ（PNG形式バイト列）のリスト
    """
    import tempfile
    import os

    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_path = tmp_file.name

    try:
        # PDFを画像に変換
        result = pdf_to_images(tmp_path, dpi=dpi)
        return result
    finally:
        # 一時ファイルを削除
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
