"""
リトライユーティリティ

エクスポネンシャルバックオフとレート制限対応を含む
汎用リトライデコレーター
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple
import time

from app.exceptions import APIRateLimitException

logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    rate_limit_exceptions: Tuple[Type[Exception], ...] = (
        APIRateLimitException,
    )
):
    """
    非同期関数用リトライデコレーター

    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本待機時間（秒）
        max_delay: 最大待機時間（秒）
        exponential_base: エクスポネンシャルバックオフの基数
        exceptions: リトライ対象の例外
        rate_limit_exceptions: レート制限例外（特別処理）

    使用例:
        @async_retry(max_retries=3, base_delay=2.0)
        async def call_api():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded after {attempt} "
                            f"retries"
                        )
                    return result

                except rate_limit_exceptions as e:
                    last_exception = e
                    # レート制限の場合、retry_afterを尊重
                    if hasattr(e, 'retry_after') and e.retry_after:
                        wait_time = min(e.retry_after, max_delay)
                    else:
                        wait_time = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} rate limited. "
                            f"Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} "
                            f"retries due to rate limit"
                        )
                        raise

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # エクスポネンシャルバックオフ
                        wait_time = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                        logger.warning(
                            f"{func.__name__} failed: {str(e)}. "
                            f"Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} "
                            f"retries: {str(e)}"
                        )
                        raise

            # すべてのリトライが失敗した場合
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def sync_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    同期関数用リトライデコレーター

    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本待機時間（秒）
        max_delay: 最大待機時間（秒）
        exponential_base: エクスポネンシャルバックオフの基数
        exceptions: リトライ対象の例外

    使用例:
        @sync_retry(max_retries=3)
        def call_api():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"{func.__name__} succeeded after {attempt} "
                            f"retries"
                        )
                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # エクスポネンシャルバックオフ
                        wait_time = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                        logger.warning(
                            f"{func.__name__} failed: {str(e)}. "
                            f"Retrying in {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} "
                            f"retries: {str(e)}"
                        )
                        raise

            # すべてのリトライが失敗した場合
            if last_exception:
                raise last_exception

        return wrapper
    return decorator
