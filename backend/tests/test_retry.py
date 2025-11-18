"""
リトライデコレーターのテスト
"""
import pytest
import time
from app.utils.retry import async_retry, sync_retry
from app.exceptions import APIRateLimitException


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncRetry:
    """async_retryデコレーターのテスト"""

    async def test_success_no_retry(self):
        """成功ケース - リトライなし"""
        call_count = 0

        @async_retry(max_retries=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1  # 1回のみ呼ばれる

    async def test_retry_and_success(self):
        """リトライ後に成功するケース"""
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.1, exponential_base=2.0)
        async def retry_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return "success"

        start_time = time.time()
        result = await retry_then_success()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count == 3  # 3回呼ばれる
        # 待機時間の確認: 0.1秒 + 0.2秒 = 0.3秒以上
        assert elapsed_time >= 0.3

    async def test_max_retries_exceeded(self):
        """最大リトライ回数を超えて失敗"""
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.05)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_fail()

        assert call_count == 4  # 初回 + 3回リトライ = 4回

    async def test_rate_limit_with_retry_after(self):
        """レート制限例外のretry_after対応"""
        call_count = 0

        @async_retry(
            max_retries=2,
            base_delay=1.0,
            rate_limit_exceptions=(APIRateLimitException,)
        )
        async def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APIRateLimitException(
                    "Rate limited",
                    retry_after=0.1  # 0.1秒後にリトライ
                )
            return "success"

        start_time = time.time()
        result = await rate_limited_function()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count == 2
        # retry_afterの0.1秒を優先
        assert 0.1 <= elapsed_time < 0.5

    async def test_max_delay_cap(self):
        """最大遅延時間の上限テスト"""
        call_count = 0

        @async_retry(
            max_retries=5,
            base_delay=10.0,  # 大きな基本遅延
            max_delay=0.2,    # 最大0.2秒に制限
            exponential_base=2.0
        )
        async def capped_delay():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test error")
            return "success"

        start_time = time.time()
        result = await capped_delay()
        elapsed_time = time.time() - start_time

        assert result == "success"
        # max_delayで制限されるため、0.2秒 * 2回 = 0.4秒程度
        assert elapsed_time < 1.0  # 制限なしなら10秒以上かかるはず


@pytest.mark.unit
class TestSyncRetry:
    """sync_retryデコレーターのテスト"""

    def test_success_no_retry(self):
        """成功ケース - リトライなし"""
        call_count = 0

        @sync_retry(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_and_success(self):
        """リトライ後に成功するケース"""
        call_count = 0

        @sync_retry(max_retries=3, base_delay=0.1)
        def retry_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"

        start_time = time.time()
        result = retry_then_success()
        elapsed_time = time.time() - start_time

        assert result == "success"
        assert call_count == 2
        # 0.1秒以上待機
        assert elapsed_time >= 0.1

    def test_max_retries_exceeded(self):
        """最大リトライ回数を超えて失敗"""
        call_count = 0

        @sync_retry(max_retries=2, base_delay=0.05)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")

        with pytest.raises(RuntimeError, match="Always fails"):
            always_fail()

        assert call_count == 3  # 初回 + 2回リトライ = 3回
