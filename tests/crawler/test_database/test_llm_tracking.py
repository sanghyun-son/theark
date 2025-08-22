"""Tests for LLM request tracking."""

import tempfile
from pathlib import Path

import pytest

from crawler.database import LLMDatabaseManager, LLMRequest, LLMUsageStats


class TestLLMTracking:
    """Test LLM request tracking functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield str(Path(temp_dir) / "test_llm.db")

    @pytest.fixture
    def llm_db_manager(self, temp_db_path):
        """Create LLM database manager for testing."""
        manager = LLMDatabaseManager(temp_db_path)
        manager.start_sync()
        yield manager
        manager.stop_sync()

    def test_create_llm_request(self, llm_db_manager):
        """Test creating LLM request records."""
        request = LLMRequest(
            model="gpt-4o-mini",
            provider="openai",
            endpoint="/v1/chat/completions",
            custom_id="test-paper-123",
            is_batched=False,
            request_type="chat",
            status="pending",
            metadata={"test": "data"},
        )

        with llm_db_manager.db_manager:
            request_id = llm_db_manager.repository.create(request)

        assert request_id is not None
        assert request_id > 0

        # Retrieve the request
        with llm_db_manager.db_manager:
            retrieved = llm_db_manager.repository.get_by_id(request_id)

        assert retrieved is not None
        assert retrieved.model == "gpt-4o-mini"
        assert retrieved.custom_id == "test-paper-123"
        assert retrieved.status == "pending"
        assert retrieved.metadata == {"test": "data"}

    def test_update_request_status(self, llm_db_manager):
        """Test updating request status and metrics."""
        request = LLMRequest(
            model="gpt-4o-mini", custom_id="test-update", status="pending"
        )

        with llm_db_manager.db_manager:
            request_id = llm_db_manager.repository.create(request)

            # Update with success status and tokens
            llm_db_manager.repository.update_status(
                request_id=request_id,
                status="success",
                response_time_ms=1500,
                tokens={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
                http_status_code=200,
            )

            # Retrieve updated request
            updated = llm_db_manager.repository.get_by_id(request_id)

        assert updated.status == "success"
        assert updated.response_time_ms == 1500
        assert updated.prompt_tokens == 100
        assert updated.completion_tokens == 50
        assert updated.total_tokens == 150
        assert updated.http_status_code == 200

    def test_get_by_custom_id(self, llm_db_manager):
        """Test retrieving requests by custom ID."""
        # Create multiple requests with same custom ID
        custom_id = "paper-456"

        for i in range(3):
            request = LLMRequest(
                model=f"gpt-{i}", custom_id=custom_id, status="success"
            )
            with llm_db_manager.db_manager:
                llm_db_manager.repository.create(request)

        # Retrieve by custom ID
        with llm_db_manager.db_manager:
            requests = llm_db_manager.repository.get_by_custom_id(custom_id)

        assert len(requests) == 3
        for request in requests:
            assert request.custom_id == custom_id

    def test_usage_stats(self, llm_db_manager):
        """Test usage statistics calculation."""
        # Create test data
        test_requests = [
            LLMRequest(
                model="gpt-4o-mini",
                status="success",
                total_tokens=100,
                response_time_ms=1000,
            ),
            LLMRequest(
                model="gpt-4o-mini",
                status="success",
                total_tokens=150,
                response_time_ms=1500,
            ),
            LLMRequest(
                model="gpt-3.5-turbo",
                status="error",
                total_tokens=0,
                response_time_ms=500,
            ),
        ]

        with llm_db_manager.db_manager:
            for request in test_requests:
                llm_db_manager.repository.create(request)

            stats = llm_db_manager.repository.get_usage_stats()

        assert stats.total_requests == 3
        assert stats.successful_requests == 2
        assert stats.failed_requests == 1
        assert stats.total_tokens == 250  # 100 + 150 + 0
        assert stats.average_response_time_ms == 1000.0  # (1000 + 1500 + 500) / 3
        assert stats.most_used_model == "gpt-4o-mini"

    def test_recent_requests(self, llm_db_manager):
        """Test retrieving recent requests."""
        # Create test requests
        for i in range(5):
            request = LLMRequest(
                model=f"model-{i}", custom_id=f"test-{i}", status="success"
            )
            with llm_db_manager.db_manager:
                llm_db_manager.repository.create(request)

        # Get recent requests (limit 3)
        with llm_db_manager.db_manager:
            recent = llm_db_manager.repository.get_recent(limit=3)

        assert len(recent) == 3
        # Should be ordered by timestamp DESC, so most recent first
        assert recent[0].custom_id == "test-4"
        assert recent[1].custom_id == "test-3"
        assert recent[2].custom_id == "test-2"

    def test_llm_request_validation(self):
        """Test LLM request model validation."""
        # Test invalid status
        with pytest.raises(ValueError, match="Invalid status"):
            LLMRequest(model="test", status="invalid_status")

        # Test invalid timestamp
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            LLMRequest(model="test", timestamp="invalid-timestamp")

    def test_cost_calculation(self):
        """Test cost calculation based on OpenAI pricing."""
        # Test GPT-4o-mini pricing
        request = LLMRequest(
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            is_batched=False,
        )

        calculated_cost = request.calculate_cost()

        # Verify cost is calculated and positive
        assert calculated_cost > 0
        assert isinstance(calculated_cost, float)

        # Test batch discount (50% off)
        request_batch = LLMRequest(
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            is_batched=True,
        )

        batch_cost = request_batch.calculate_cost()
        assert abs(batch_cost - calculated_cost * 0.5) < 0.000001

        # Test GPT-5-mini pricing
        request_gpt5 = LLMRequest(
            model="gpt-5-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            is_batched=False,
        )

        gpt5_cost = request_gpt5.calculate_cost()
        assert gpt5_cost > 0
        assert isinstance(gpt5_cost, float)

        # Test GPT-4.1-mini pricing
        request_gpt41 = LLMRequest(
            model="gpt-4.1-mini",
            prompt_tokens=1000,
            completion_tokens=500,
            is_batched=False,
        )

        gpt41_cost = request_gpt41.calculate_cost()
        assert gpt41_cost > 0
        assert isinstance(gpt41_cost, float)

        # Test with missing tokens (should return 0)
        request_no_tokens = LLMRequest(
            model="gpt-4o-mini",
            prompt_tokens=None,
            completion_tokens=None,
        )

        assert request_no_tokens.calculate_cost() == 0.0

        # Test unknown model (should use default pricing)
        request_unknown = LLMRequest(
            model="unknown-model",
            prompt_tokens=1000,
            completion_tokens=500,
            is_batched=False,
        )

        unknown_cost = request_unknown.calculate_cost()
        assert unknown_cost > 0
        assert isinstance(unknown_cost, float)

        # Test that different models have different costs
        assert (
            abs(gpt5_cost - calculated_cost) > 0.000001
        )  # GPT-5-mini should cost more than GPT-4o-mini
        assert (
            abs(gpt41_cost - calculated_cost) > 0.000001
        )  # GPT-4.1-mini should cost more than GPT-4o-mini

    def test_database_path_handling(self):
        """Test database path handling for different environments."""
        # Test with custom path
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = str(Path(temp_dir) / "custom_llm.db")
            manager = LLMDatabaseManager(custom_path)
            assert str(manager.db_path) == custom_path

        # Test default path (should use appropriate directory based on environment)
        manager = LLMDatabaseManager()
        assert manager.db_path.name == "llm_requests.db"
        # In test environment, uses /tmp/theark_test; in dev/prod, uses ./db
        assert "theark_test" in str(manager.db_path) or "db" in str(manager.db_path)
