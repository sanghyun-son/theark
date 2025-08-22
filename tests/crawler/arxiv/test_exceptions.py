"""Tests for arXiv custom exceptions."""

import pytest

from crawler.arxiv.exceptions import (
    ArxivAPIError,
    ArxivError,
    ArxivNotFoundError,
    ArxivRateLimitError,
    ArxivTimeoutError,
)


class TestArxivExceptions:
    """Test custom arXiv exceptions."""

    def test_arxiv_error_inheritance(self):
        """Test that all exceptions inherit from ArxivError."""
        assert issubclass(ArxivNotFoundError, ArxivError)
        assert issubclass(ArxivAPIError, ArxivError)
        assert issubclass(ArxivTimeoutError, ArxivError)
        assert issubclass(ArxivRateLimitError, ArxivError)

    def test_arxiv_error_instantiation(self):
        """Test that exceptions can be instantiated with messages."""
        error = ArxivError("Test error")
        assert str(error) == "Test error"

    def test_arxiv_not_found_error(self):
        """Test ArxivNotFoundError."""
        error = ArxivNotFoundError("Paper not found")
        assert str(error) == "Paper not found"
        assert isinstance(error, ArxivError)

    def test_arxiv_api_error(self):
        """Test ArxivAPIError."""
        error = ArxivAPIError("API error")
        assert str(error) == "API error"
        assert isinstance(error, ArxivError)

    def test_arxiv_timeout_error(self):
        """Test ArxivTimeoutError."""
        error = ArxivTimeoutError("Request timeout")
        assert str(error) == "Request timeout"
        assert isinstance(error, ArxivError)

    def test_arxiv_rate_limit_error(self):
        """Test ArxivRateLimitError."""
        error = ArxivRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, ArxivError)

    def test_exception_catching(self):
        """Test that exceptions can be caught properly."""
        try:
            raise ArxivNotFoundError("Paper not found")
        except ArxivNotFoundError as e:
            assert str(e) == "Paper not found"
        except ArxivError:
            pytest.fail("Should not catch ArxivError")
        except Exception:
            pytest.fail("Should not catch generic Exception")

    def test_base_exception_catching(self):
        """Test that base ArxivError can catch all arXiv exceptions."""
        exceptions = [
            ArxivNotFoundError("Not found"),
            ArxivAPIError("API error"),
            ArxivTimeoutError("Timeout"),
            ArxivRateLimitError("Rate limit"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except ArxivError as e:
                assert isinstance(e, ArxivError)
            except Exception:
                pytest.fail(f"Should catch {type(exc).__name__} as ArxivError")
