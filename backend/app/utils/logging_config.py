"""
構造化ログ設定

アプリケーション全体で使用するロガー設定
"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """色付きログフォーマッター（開発用）"""

    # ANSI カラーコード
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        # レベル名に色を付ける
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    enable_colors: bool = True,
    log_file: Optional[str] = None
):
    """
    ログ設定を初期化

    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        enable_colors: 色付きログを有効にするか
        log_file: ログファイルパス（Noneの場合はファイル出力なし）
    """
    # ルートロガーを取得
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # フォーマット
    detailed_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )

    if enable_colors:
        formatter = ColoredFormatter(detailed_format)
    else:
        formatter = logging.Formatter(detailed_format)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ファイルハンドラー（オプション）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(detailed_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # サードパーティライブラリのログレベルを調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.info(f"Logging initialized with level: {log_level}")
