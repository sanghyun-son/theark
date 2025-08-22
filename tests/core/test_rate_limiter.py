"""Tests for AsyncRateLimiter."""

import asyncio
import time
import pytest

from core.rate_limiter import AsyncRateLimiter


class TestAsyncRateLimiter:
    """Test AsyncRateLimiter functionality."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)
        assert limiter.requests_per_second == 2.0
        assert limiter.min_interval == 0.5
        assert limiter.last_request_time is None

    def test_initialization_with_invalid_rate(self):
        """Test initialization with invalid rate."""
        with pytest.raises(
            ValueError, match="requests_per_second must be positive"
        ):
            AsyncRateLimiter(requests_per_second=0)

        with pytest.raises(
            ValueError, match="requests_per_second must be positive"
        ):
            AsyncRateLimiter(requests_per_second=-1.0)

    @pytest.mark.asyncio
    async def test_first_wait_no_delay(self):
        """Test that first wait doesn't delay."""
        limiter = AsyncRateLimiter(requests_per_second=1.0)

        start_time = time.time()
        await limiter.wait()
        elapsed = time.time() - start_time

        # First wait should be nearly instantaneous
        assert elapsed < 0.1
        assert limiter.last_request_time is not None

    @pytest.mark.asyncio
    async def test_subsequent_waits_respect_rate_limit(self):
        """Test that subsequent waits respect the rate limit."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval

        # First wait
        await limiter.wait()
        first_time = limiter.last_request_time

        # Second wait should be delayed
        start_time = time.time()
        await limiter.wait()
        elapsed = time.time() - start_time

        # Should have waited approximately 0.5 seconds
        assert 0.4 <= elapsed <= 0.6
        assert limiter.last_request_time > first_time

    @pytest.mark.asyncio
    async def test_high_rate_limit(self):
        """Test with high rate limit (small intervals)."""
        limiter = AsyncRateLimiter(requests_per_second=10.0)  # 0.1s interval

        await limiter.wait()  # First call

        start_time = time.time()
        await limiter.wait()  # Second call
        elapsed = time.time() - start_time

        # Should have waited approximately 0.1 seconds
        assert 0.05 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_multiple_rapid_calls(self):
        """Test multiple rapid calls respect rate limit."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval

        start_time = time.time()

        # Make 3 calls
        await limiter.wait()
        await limiter.wait()
        await limiter.wait()

        total_elapsed = time.time() - start_time

        # Should take at least 1 second (2 intervals of 0.5s each)
        assert total_elapsed >= 0.9

    @pytest.mark.asyncio
    async def test_rate_limit_accuracy(self):
        """Test that rate limiting is reasonably accurate."""
        limiter = AsyncRateLimiter(requests_per_second=1.0)  # 1s interval

        times = []

        for _ in range(3):
            start = time.time()
            await limiter.wait()
            times.append(time.time() - start)

        # First call should be fast
        assert times[0] < 0.1

        # Subsequent calls should be around 1 second
        assert 0.8 <= times[1] <= 1.2
        assert 0.8 <= times[2] <= 1.2

    @pytest.mark.asyncio
    async def test_concurrent_waits_with_gather(self):
        """Test concurrent waits using asyncio.gather."""
        limiter1 = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval
        limiter2 = AsyncRateLimiter(requests_per_second=1.0)  # 1.0s interval

        # Start both limiters
        await limiter1.wait()
        await limiter2.wait()

        # Use gather to run both waits concurrently
        start_time = time.time()
        await asyncio.gather(
            limiter1.wait(),  # Should wait ~0.5s
            limiter2.wait(),  # Should wait ~1.0s
        )
        total_elapsed = time.time() - start_time

        # The total time should be approximately the longer of the two waits
        # (since they run concurrently, not sequentially)
        assert 0.8 <= total_elapsed <= 1.2

        # Both limiters should have updated their last request times
        assert limiter1.last_request_time > start_time
        assert limiter2.last_request_time > start_time

    @pytest.mark.asyncio
    async def test_multiple_concurrent_limiters(self):
        """Test multiple limiters with concurrent operations."""
        limiters = [
            AsyncRateLimiter(requests_per_second=2.0),  # 0.5s interval
            AsyncRateLimiter(requests_per_second=1.0),  # 1.0s interval
            AsyncRateLimiter(requests_per_second=4.0),  # 0.25s interval
        ]

        # Initialize all limiters
        for limiter in limiters:
            await limiter.wait()

        # Run concurrent waits
        start_time = time.time()
        await asyncio.gather(*[limiter.wait() for limiter in limiters])
        total_elapsed = time.time() - start_time

        # Should complete in approximately the time of the slowest limiter
        assert 0.8 <= total_elapsed <= 1.2

        # All limiters should have updated their timestamps
        for limiter in limiters:
            assert limiter.last_request_time > start_time

    @pytest.mark.asyncio
    async def test_iterate(self):
        """Test basic iteration with rate limiting."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval
        processed_items = []

        async def processor(item: int) -> None:
            processed_items.append(item)

        items = [1, 2, 3]
        start_time = time.time()
        await limiter.iterate(items, processor)
        total_elapsed = time.time() - start_time

        # Should process all items
        assert processed_items == [1, 2, 3]
        # Should take at least 1 second (2 intervals of 0.5s each)
        assert total_elapsed >= 0.9

    @pytest.mark.asyncio
    async def test_iterate_with_results(self):
        """Test iteration with results collection."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval

        async def processor(item: int) -> int:
            return item * 2

        items = [1, 2, 3]
        start_time = time.time()
        results = await limiter.iterate_with_results(items, processor)
        total_elapsed = time.time() - start_time

        # Should return processed results
        assert results == [2, 4, 6]
        # Should take at least 1 second (2 intervals of 0.5s each)
        assert total_elapsed >= 0.9

    @pytest.mark.asyncio
    async def test_iterate_concurrent(self):
        """Test concurrent iteration with rate limiting."""
        limiter = AsyncRateLimiter(requests_per_second=2.0)  # 0.5s interval
        processed_items = []

        async def processor(item: int) -> None:
            processed_items.append(item)
            await asyncio.sleep(0.1)  # Simulate some work

        items = [1, 2, 3, 4, 5]
        start_time = time.time()
        await limiter.iterate_concurrent(items, processor, max_concurrent=2)
        total_elapsed = time.time() - start_time

        # Should process all items
        assert set(processed_items) == {1, 2, 3, 4, 5}
        # Should be faster than sequential but still respect rate limits
        assert total_elapsed >= 0.9  # At least 2 intervals
        assert (
            total_elapsed < 3.0
        )  # But faster than sequential (5 * 0.5s = 2.5s)

    @pytest.mark.asyncio
    async def test_iterate_empty_list(self):
        """Test iteration with empty list."""
        limiter = AsyncRateLimiter(requests_per_second=1.0)
        processed_items = []

        async def processor(item: int) -> None:
            processed_items.append(item)

        # Should not raise any errors
        await limiter.iterate([], processor)
        await limiter.iterate_with_results([], processor)
        await limiter.iterate_concurrent([], processor)

        assert processed_items == []

    @pytest.mark.asyncio
    async def test_iterate_concurrent_semaphore_limit(self):
        """Test that concurrent iteration respects semaphore limits."""
        limiter = AsyncRateLimiter(requests_per_second=10.0)  # Fast rate
        active_tasks = 0
        max_active = 0

        async def processor(item: int) -> None:
            nonlocal active_tasks, max_active
            active_tasks += 1
            max_active = max(max_active, active_tasks)
            await asyncio.sleep(0.1)  # Simulate work
            active_tasks -= 1

        items = list(range(10))
        await limiter.iterate_concurrent(items, processor, max_concurrent=3)

        # Should never exceed max_concurrent
        assert max_active <= 3
