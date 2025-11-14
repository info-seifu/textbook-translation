"""
Supabase クライアント設定
"""
from supabase import create_client, Client
from app.config import settings


def get_supabase_client() -> Client:
    """
    Supabaseクライアントを取得

    Returns:
        Client: Supabaseクライアント
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY
    )


def get_supabase_admin_client() -> Client:
    """
    Supabase管理者クライアントを取得（サービスキー使用）

    Returns:
        Client: Supabase管理者クライアント
    """
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_KEY
    )


# グローバルクライアント（オプション）
supabase: Client = get_supabase_client()
