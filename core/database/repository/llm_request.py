"""Repository for LLM request tracking."""

from sqlmodel import Session, select

from core.database.repository.base import BaseRepository
from core.models.domain.llm_usage_stats import (
    CostSummary,
    ModelUsageStats,
    UsageStatsResponse,
)
from core.models.rows import LLMRequest


class LLMRequestRepository(BaseRepository[LLMRequest]):
    """Repository for LLM request tracking."""

    def __init__(self, db_session: Session):
        """Initialize with DB session."""
        super().__init__(LLMRequest, db_session)

    def get_requests_by_date_range(
        self,
        start_date: str,
        end_date: str,
    ) -> list[LLMRequest]:
        """Get LLM requests within a date range."""
        stmt = select(LLMRequest).where(
            LLMRequest.timestamp >= start_date,
            LLMRequest.timestamp <= end_date,
        )
        return list(self.db.exec(stmt).all())

    def get_cost_summary_by_date(self, date: str) -> CostSummary:
        """Get cost summary for a specific date."""
        stmt = select(LLMRequest).where(
            LLMRequest.timestamp >= date,
            LLMRequest.timestamp < f"{date} 23:59:59",
            LLMRequest.status == "success",
        )
        requests = list(self.db.exec(stmt).all())

        total_cost = sum(request.estimated_cost_usd or 0.0 for request in requests)

        return CostSummary(
            total_cost_usd=round(total_cost, 6),
            request_count=len(requests),
            date=date,
        )

    def get_model_usage_stats(
        self,
        start_date: str,
        end_date: str,
    ) -> UsageStatsResponse:
        """Get usage statistics by model."""
        stmt = select(LLMRequest).where(
            LLMRequest.timestamp >= start_date,
            LLMRequest.timestamp <= end_date,
        )
        requests = list(self.db.exec(stmt).all())

        model_stats: dict[str, ModelUsageStats] = {}
        total_requests = 0
        total_cost = 0.0

        for request in requests:
            model = request.model
            if model not in model_stats:
                model_stats[model] = ModelUsageStats()

            stats = model_stats[model]
            stats.total_requests += 1
            total_requests += 1

            if request.status == "success":
                stats.successful_requests += 1
                if request.total_tokens:
                    stats.total_tokens += request.total_tokens
                if request.estimated_cost_usd:
                    stats.total_cost_usd += request.estimated_cost_usd
                    total_cost += request.estimated_cost_usd
                if request.response_time_ms:
                    stats.avg_response_time_ms += request.response_time_ms
            else:
                stats.failed_requests += 1

        # 평균 응답 시간 계산 및 비용 반올림
        for stats in model_stats.values():
            if stats.successful_requests > 0:
                stats.avg_response_time_ms = round(
                    stats.avg_response_time_ms / stats.successful_requests, 2
                )
            stats.total_cost_usd = round(stats.total_cost_usd, 6)

        return UsageStatsResponse(
            models=model_stats,
            total_requests=total_requests,
            total_cost_usd=round(total_cost, 6),
            period={"start_date": start_date, "end_date": end_date},
        )

    def get_requests_by_status(self, status: str) -> list[LLMRequest]:
        """Get LLM requests by status."""
        stmt = select(LLMRequest).where(LLMRequest.status == status)
        return list(self.db.exec(stmt).all())

    def get_total_cost_by_period(
        self,
        start_date: str,
        end_date: str,
    ) -> float:
        """Get total cost for a period."""
        stmt = select(LLMRequest).where(
            LLMRequest.timestamp >= start_date,
            LLMRequest.timestamp <= end_date,
            LLMRequest.status == "success",
        )
        requests = list(self.db.exec(stmt).all())

        return sum(request.estimated_cost_usd or 0.0 for request in requests)
