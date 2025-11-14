"""
ローカルファイルストレージ管理
Supabaseの代わりにローカルファイルシステムを使用
"""
from typing import Optional
from pathlib import Path


class LocalStorage:
    """ローカルファイルストレージ"""

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # バケット（ディレクトリ）の作成
        self.buckets = {
            'pdfs': self.base_dir / 'pdfs',
            'documents': self.base_dir / 'documents',
            'figures': self.base_dir / 'figures'
        }

        for bucket in self.buckets.values():
            bucket.mkdir(exist_ok=True)

    def upload(self, bucket: str, file_path: str, content: bytes, options: Optional[dict] = None) -> str:
        """
        ファイルをアップロード

        Args:
            bucket: バケット名（pdfs/documents/figures）
            file_path: ファイルパス（例: {job_id}/original.pdf）
            content: ファイル内容（バイト）
            options: オプション（無視）

        Returns:
            保存されたファイルパス
        """
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")

        full_path = self.buckets[bucket] / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイル書き込み
        with open(full_path, 'wb') as f:
            f.write(content)

        return str(full_path)

    def download(self, bucket: str, file_path: str) -> bytes:
        """
        ファイルをダウンロード

        Args:
            bucket: バケット名
            file_path: ファイルパス

        Returns:
            ファイル内容（バイト）
        """
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")

        full_path = self.buckets[bucket] / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, 'rb') as f:
            return f.read()

    def get_public_url(self, bucket: str, file_path: str) -> str:
        """
        公開URLを取得（ローカルの場合はファイルパス）

        Args:
            bucket: バケット名
            file_path: ファイルパス

        Returns:
            ローカルファイルパス（URLの代わり）
        """
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")

        full_path = self.buckets[bucket] / file_path
        return f"file://{full_path.absolute()}"

    def delete(self, bucket: str, file_path: str):
        """ファイルを削除"""
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")

        full_path = self.buckets[bucket] / file_path

        if full_path.exists():
            full_path.unlink()

    def exists(self, bucket: str, file_path: str) -> bool:
        """ファイルの存在確認"""
        if bucket not in self.buckets:
            raise ValueError(f"Unknown bucket: {bucket}")

        full_path = self.buckets[bucket] / file_path
        return full_path.exists()


# ストレージバケットクラス（Supabase互換インターフェース）
class StorageBucket:
    """ストレージバケット（Supabase互換）"""

    def __init__(self, storage: LocalStorage, bucket_name: str):
        self.storage = storage
        self.bucket_name = bucket_name

    def upload(self, path: str, content: bytes, options: Optional[dict] = None):
        """ファイルアップロード"""
        return self.storage.upload(self.bucket_name, path, content, options)

    def download(self, path: str) -> bytes:
        """ファイルダウンロード"""
        return self.storage.download(self.bucket_name, path)

    def get_public_url(self, path: str) -> str:
        """公開URL取得"""
        return self.storage.get_public_url(self.bucket_name, path)

    def delete(self, path: str):
        """ファイル削除"""
        return self.storage.delete(self.bucket_name, path)


# ストレージクライアント（Supabase互換インターフェース）
class LocalStorageClient:
    """ローカルストレージクライアント（Supabase互換）"""

    def __init__(self, base_dir: str = "storage"):
        self.storage = LocalStorage(base_dir)

    def from_(self, bucket_name: str) -> StorageBucket:
        """バケットを取得"""
        return StorageBucket(self.storage, bucket_name)


# グローバルインスタンス
_local_storage = LocalStorageClient()


def get_local_storage() -> LocalStorageClient:
    """ローカルストレージクライアントを取得"""
    return _local_storage
