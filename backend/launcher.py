"""
教科書翻訳システム - Windows .exe ランチャー

このスクリプトは:
1. FastAPIサーバーを起動
2. 自動的にブラウザを開く
3. 終了時に適切にシャットダウン
"""
import sys
import webbrowser
import threading
import time
import uvicorn
from pathlib import Path

# アプリケーションのルートディレクトリを設定
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.config import settings  # noqa: E402


def open_browser(url: str, delay: float = 2.0):
    """
    指定秒数後にブラウザを開く

    Args:
        url: 開くURL
        delay: 待機時間（秒）
    """
    def _open():
        time.sleep(delay)
        print(f"🌐 ブラウザを起動中: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️ ブラウザの起動に失敗: {e}")
            print(f"手動でブラウザを開き、以下のURLにアクセスしてください: {url}")

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("📚 教科書翻訳システム")
    print("=" * 60)
    print()

    # サーバー設定
    host = settings.BACKEND_HOST
    port = settings.BACKEND_PORT
    url = f"http://{host}:{port}"

    print("🚀 サーバーを起動中...")
    print(f"   URL: {url}")
    print()
    print("⚠️ 終了するには Ctrl+C を押してください")
    print("=" * 60)
    print()

    # ブラウザを自動起動（2秒後）
    open_browser(url, delay=2.0)

    # FastAPIサーバー起動
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("👋 サーバーを終了しています...")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("\n以下を確認してください:")
        print(f"  - ポート {port} が他のプログラムで使用されていないか")
        print("  - 環境変数が正しく設定されているか (.env ファイル)")
        print()
        input("Enterキーを押して終了...")
        sys.exit(1)


if __name__ == "__main__":
    main()
