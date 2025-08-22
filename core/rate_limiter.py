"""Async rate limiter for controlling request frequency."""

import asyncio
import time
from typing import Optional, TypeVar, Callable, Awaitable

from core.log import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class AsyncRateLimiter:
    """Async rate limiter for controlling request frequency."""

    def __init__(self, requests_per_second: float = 1.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests allowed per second.
                                Default is 1.0 for conservative rate limiting.
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time: Optional[float] = None

    async def wait(self) -> None:
        """Wait if necessary to respect rate limits."""
        if self.last_request_time is None:
            self.last_request_time = time.time()
            return

        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    async def _process_items(
        self, items: list[T], processor: Callable[[T], Awaitable[T]]
    ) -> list[T]:
        """Internal method to process items with rate limiting."""
        results = []
        for item in items:
            await self.wait()
            result = await processor(item)
            results.append(result)
        return results

    async def iterate(
        self, items: list[T], processor: Callable[[T], Awaitable[None]]
    ) -> None:
        """Process items with rate limiting.

        Args:
            items: List of items to process
            processor: Async function to process each item
        """
        await self._process_items(items, processor)

    async def iterate_with_results(
        self, items: list[T], processor: Callable[[T], Awaitable[T]]
    ) -> list[T]:
        """Process items with rate limiting and return results.

        Args:
            items: List of items to process
            processor: Async function to process each item and return result

        Returns:
            List of processed results
        """
        return await self._process_items(items, processor)

    async def iterate_concurrent(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[None]],
        max_concurrent: int = 3,
    ) -> None:
        """Process items concurrently with rate limiting.

        Args:
            items: List of items to process
            processor: Async function to process each item
            max_concurrent: Maximum number of concurrent operations
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(item: T) -> None:
            async with semaphore:
                await self.wait()
                await processor(item)

        tasks = [process_with_semaphore(item) for item in items]
        await asyncio.gather(*tasks)
