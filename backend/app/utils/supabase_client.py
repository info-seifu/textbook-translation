"""
データベースクライアント設定
ローカル環境ではJSONベースのデータベースを使用
"""
from app.utils.local_db import get_local_db
from app.utils.local_storage import get_local_storage


class LocalClient:
    """ローカルクライアント（Supabase互換）"""

    def __init__(self):
        self._db = get_local_db()
        self._storage = get_local_storage()

    def table(self, table_name: str):
        """テーブルを取得"""
        return self._db.table(table_name)

    @property
    def storage(self):
        """ストレージを取得"""
        return self._storage


def get_supabase_client():
    """
    データベースクライアントを取得（ローカル版）

    Returns:
        LocalClient: ローカルクライアント
    """
    return LocalClient()


def get_supabase_admin_client():
    """
    管理者クライアントを取得（ローカル版）

    Returns:
        LocalClient: ローカルクライアント
    """
    return LocalClient()


# グローバルクライアント
supabase = get_supabase_client()
