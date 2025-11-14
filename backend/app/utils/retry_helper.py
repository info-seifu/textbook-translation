"""
リトライヘルパー
API呼び出しのリトライとエラーハンドリングを提供
"""
import asyncio
from typing import Callable, Any, TypeVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_async(
    func: Callable[..., Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    非同期関数のリトライ実行

    Args:
        func: 実行する非同期関数
        max_retries: 最大リトライ回数
        initial_delay: 初回リトライまでの待機時間（秒）
        backoff_factor: 指数バックオフの係数
        max_delay: 最大待機時間（秒）
        exceptions: リトライ対象の例外タプル

    Returns:
        関数の実行結果

    Raises:
        最後のリトライで発生した例外
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            result = await func()
            return result
        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"Failed after {max_retries} retries: {str(e)}")
                raise

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                f"Retrying in {delay:.1f}s..."
            )

            await asyncio.sleep(delay)

            # 指数バックオフ
            delay = min(delay * backoff_factor, max_delay)

    # このコードには到達しないはずだが、型チェッカーのために
    raise last_exception


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
):
    """
    リトライ機能を提供するデコレーター

    使用例:
        @with_retry(max_retries=3, initial_delay=2.0)
        async def my_function():
            # API呼び出しなど
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay,
                exceptions=exceptions
            )
        return wrapper
    return decorator


class RetryConfig:
    """リトライ設定"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay


# デフォルト設定
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=2.0,
    max_delay=30.0
)

# API呼び出し用の設定（より長いタイムアウトとリトライ）
API_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    initial_delay=3.0,
    backoff_factor=2.0,
    max_delay=60.0
)
