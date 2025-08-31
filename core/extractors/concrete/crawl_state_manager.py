"""Crawl execution state manager for coordinating crawler workers."""

from datetime import datetime, timedelta

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from core.log import get_logger
from core.models.rows import CrawlExecutionState

logger = get_logger(__name__)


class CrawlStateManager:
    """Manages crawl execution state for coordinating crawler workers."""

    def __init__(self, engine: Engine):
        """Initialize the crawl state manager.

        Args:
            engine: Database engine
        """
        self.engine = engine

    def get_or_create_state(self) -> CrawlExecutionState:
        """Get existing state or create new one.

        Returns:
            CrawlExecutionState instance
        """
        with Session(self.engine) as session:
            state = session.exec(select(CrawlExecutionState)).first()

            if state is None:
                # Create new state
                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

                state = CrawlExecutionState(
                    last_execution_date=today,
                    historical_crawl_date=yesterday,
                    historical_crawl_index=0,
                    today_crawler_active=True,
                    historical_crawler_active=True,
                )
                session.add(state)
                session.commit()
                session.refresh(state)
                logger.info(f"Created new crawl execution state: {state}")
            else:
                logger.info(f"Found existing crawl execution state: {state}")

            return state

    def update_last_execution_date(self, date: str) -> None:
        """Update the last execution date.

        Args:
            date: Date in YYYY-MM-DD format
        """
        with Session(self.engine) as session:
            state = session.exec(select(CrawlExecutionState)).first()
            if state:
                state.last_execution_date = date
                state.updated_at = datetime.now().isoformat()
                session.commit()
                logger.info(f"Updated last execution date to: {date}")

    def update_historical_crawl_progress(self, date: str, index: int) -> None:
        """Update historical crawl progress.

        Args:
            date: Current crawl date in YYYY-MM-DD format
            index: Current crawl index
        """
        with Session(self.engine) as session:
            state = session.exec(select(CrawlExecutionState)).first()
            if state:
                state.historical_crawl_date = date
                state.historical_crawl_index = index
                state.updated_at = datetime.now().isoformat()
                session.commit()
                logger.info(
                    f"Updated historical crawl progress: {date}, index: {index}"
                )

    def set_crawler_active(self, crawler_type: str, active: bool) -> None:
        """Set crawler active status.

        Args:
            crawler_type: Either 'today' or 'historical'
            active: Active status
        """
        state = self.get_or_create_state()

        if crawler_type == "today":
            state.today_crawler_active = active
        elif crawler_type == "historical":
            state.historical_crawler_active = active
        else:
            raise ValueError(f"Invalid crawler type: {crawler_type}")

        # Update in database
        with Session(self.engine) as session:
            db_state = session.exec(select(CrawlExecutionState)).first()
            if db_state:
                if crawler_type == "today":
                    db_state.today_crawler_active = active
                elif crawler_type == "historical":
                    db_state.historical_crawler_active = active

                db_state.updated_at = datetime.now().isoformat()
                session.commit()
                logger.info(f"Set {crawler_type} crawler active: {active}")

    def get_historical_crawl_range(self) -> tuple[str, str]:
        """Get the date range for historical crawling.

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        state = self.get_or_create_state()

        # Start from yesterday (today - 1)
        start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # End at the last execution date (or 2015-01-01 if earlier)
        end_date = state.last_execution_date
        hard_limit = "2015-01-01"

        # Ensure we don't go before the hard limit
        if end_date < hard_limit:
            end_date = hard_limit

        logger.info(f"Historical crawl range: {start_date} to {end_date}")
        return start_date, end_date

    def is_crawler_active(self, crawler_type: str) -> bool:
        """Check if a crawler is active.

        Args:
            crawler_type: Either 'today' or 'historical'

        Returns:
            True if crawler is active
        """
        state = self.get_or_create_state()

        if crawler_type == "today":
            return state.today_crawler_active
        elif crawler_type == "historical":
            return state.historical_crawler_active
        else:
            raise ValueError(f"Invalid crawler type: {crawler_type}")

    def get_current_historical_crawl_state(self) -> tuple[str, int]:
        """Get current historical crawl state.

        Returns:
            Tuple of (current_date, current_index)
        """
        state = self.get_or_create_state()
        return state.historical_crawl_date, state.historical_crawl_index
