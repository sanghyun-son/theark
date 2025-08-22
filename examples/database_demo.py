#!/usr/bin/env python3
"""Demonstration of the arXiv crawler database system."""

from core.log import setup_test_logging, get_logger
from crawler.database import (
    SQLiteManager,
    setup_database_environment,
    Paper,
    Summary,
    AppUser,
    UserInterest,
    UserStar,
    FeedItem,
    CrawlEvent,
    PaperRepository,
    SummaryRepository,
    UserRepository,
    FeedRepository,
    CrawlEventRepository,
)


def main() -> None:
    """Demonstrate the database system functionality."""
    # Setup logging
    setup_test_logging()
    logger = get_logger(__name__)

    logger.info("Starting database system demonstration")

    # Setup database environment for development
    config = setup_database_environment("development")
    db_path = config.database_path

    try:
        # Initialize database
        with SQLiteManager(db_path) as db_manager:
            logger.info("Database initialized successfully")

            # Create tables
            db_manager.create_tables()
            logger.info("Database tables created")

            # Create repositories
            paper_repo = PaperRepository(db_manager)
            summary_repo = SummaryRepository(db_manager)
            user_repo = UserRepository(db_manager)
            feed_repo = FeedRepository(db_manager)
            event_repo = CrawlEventRepository(db_manager)

            # Demo 1: Paper operations
            logger.info("=== Demo 1: Paper Operations ===")

            # Create a paper
            paper = Paper(
                arxiv_id="2101.00099",
                title="Attention Is All You Need (Demo)",
                abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                primary_category="cs.CL",
                categories="cs.CL,cs.LG",
                authors="Ashish Vaswani;Noam Shazeer;Niki Parmar",
                url_abs="https://arxiv.org/abs/2101.00001",
                url_pdf="https://arxiv.org/pdf/2101.00001",
                published_at="2021-01-01T00:00:00Z",
                updated_at="2021-01-01T00:00:00Z",
            )

            paper_id = paper_repo.create(paper)
            logger.info(f"Created paper with ID: {paper_id}")

            # Retrieve the paper
            retrieved_paper = paper_repo.get_by_arxiv_id("2101.00099")
            logger.info(f"Retrieved paper: {retrieved_paper.title}")

            # Demo 2: Summary operations
            logger.info("=== Demo 2: Summary Operations ===")

            summary = Summary(
                paper_id=paper_id,
                version=1,
                overview="This paper presents the Transformer architecture as a novel approach to sequence-to-sequence modeling.",
                motivation="Existing models rely heavily on recurrent or convolutional neural networks which are slow and difficult to parallelize.",
                method="The authors propose a model based entirely on attention mechanisms, eliminating recurrence and convolutions.",
                result="The Transformer achieves new state-of-the-art results on machine translation tasks while being more parallelizable.",
                conclusion="Attention is all you need for sequence modeling, opening up new possibilities for parallelization and efficiency.",
                language="English",
                interests="attention,transformer,machine translation,neural networks",
                relevance=9,
                model="gpt-4",
            )

            summary_id = summary_repo.create(summary)
            logger.info(f"Created summary with ID: {summary_id}")

            # Demo 3: User operations
            logger.info("=== Demo 3: User Operations ===")

            user = AppUser(
                email="demo_researcher@example.com",
                display_name="AI Researcher (Demo)",
            )

            user_id = user_repo.create_user(user)
            logger.info(f"Created user with ID: {user_id}")

            # Add user interests
            interests = [
                UserInterest(
                    user_id=user_id, kind="category", value="cs.CL", weight=2.0
                ),
                UserInterest(
                    user_id=user_id,
                    kind="keyword",
                    value="transformer",
                    weight=1.5,
                ),
                UserInterest(
                    user_id=user_id,
                    kind="author",
                    value="Ashish Vaswani",
                    weight=1.0,
                ),
            ]

            for interest in interests:
                user_repo.add_interest(interest)

            logger.info("Added user interests")

            # Add a star/bookmark
            star = UserStar(
                user_id=user_id,
                paper_id=paper_id,
                note="Important paper for my research",
            )
            user_repo.add_star(star)
            logger.info("Added user star")

            # Demo 4: Feed operations
            logger.info("=== Demo 4: Feed Operations ===")

            feed_item = FeedItem(
                user_id=user_id,
                paper_id=paper_id,
                score=0.95,
                feed_date="2021-01-01",
            )

            feed_id = feed_repo.add_feed_item(feed_item)
            logger.info(f"Added feed item with ID: {feed_id}")

            # Demo 5: Crawl event logging
            logger.info("=== Demo 5: Crawl Event Logging ===")

            events = [
                CrawlEvent(
                    arxiv_id="2101.00099",
                    event_type="FOUND",
                    detail="Paper found during crawl",
                ),
                CrawlEvent(
                    arxiv_id="2101.00002",
                    event_type="SKIPPED",
                    detail="Paper already exists",
                ),
                CrawlEvent(
                    arxiv_id="2101.00003",
                    event_type="ERROR",
                    detail="Failed to parse paper",
                ),
            ]

            for event in events:
                event_id = event_repo.log_event(event)
                logger.info(
                    f"Logged event {event.event_type} with ID: {event_id}"
                )

            # Demo 6: Search functionality
            logger.info("=== Demo 6: Search Functionality ===")

            # Add more papers for search demo
            papers = [
                Paper(
                    arxiv_id="2101.00002",
                    title="BERT: Pre-training of Deep Bidirectional Transformers",
                    abstract="We introduce a new language representation model called BERT...",
                    primary_category="cs.CL",
                    categories="cs.CL",
                    authors="Jacob Devlin;Ming-Wei Chang;Kenton Lee",
                    url_abs="https://arxiv.org/abs/2101.00002",
                    published_at="2021-01-02T00:00:00Z",
                    updated_at="2021-01-02T00:00:00Z",
                ),
                Paper(
                    arxiv_id="2101.00003",
                    title="GPT-3: Language Models are Few-Shot Learners",
                    abstract="Recent work has demonstrated substantial gains on many NLP tasks...",
                    primary_category="cs.CL",
                    categories="cs.CL",
                    authors="Tom B. Brown;Benjamin Mann;Nick Ryder",
                    url_abs="https://arxiv.org/abs/2101.00003",
                    published_at="2021-01-03T00:00:00Z",
                    updated_at="2021-01-03T00:00:00Z",
                ),
            ]

            for paper in papers:
                paper_repo.create(paper)

            # Search for transformer-related papers
            search_results = paper_repo.search_by_keywords("transformer")
            logger.info(
                f"Found {len(search_results)} papers matching 'transformer'"
            )
            for result in search_results:
                logger.info(f"  - {result.title}")

            # Get recent papers
            recent_papers = paper_repo.get_recent_papers(limit=5)
            logger.info(f"Retrieved {len(recent_papers)} recent papers")

            # Demo 7: User data retrieval
            logger.info("=== Demo 7: User Data Retrieval ===")

            user_interests = user_repo.get_user_interests(user_id)
            logger.info(f"User has {len(user_interests)} interests")

            user_stars = user_repo.get_user_stars(user_id)
            logger.info(f"User has {len(user_stars)} starred papers")

            user_feed = feed_repo.get_user_feed(user_id, "2021-01-01")
            logger.info(f"User feed for 2021-01-01 has {len(user_feed)} items")

            # Demo 8: Crawl event history
            logger.info("=== Demo 8: Crawl Event History ===")

            recent_events = event_repo.get_recent_events(limit=10)
            logger.info(f"Retrieved {len(recent_events)} recent crawl events")

            for event in recent_events:
                logger.info(
                    f"  - {event.event_type}: {event.arxiv_id} - {event.detail}"
                )

                logger.info("Database demonstration completed successfully")

    except Exception as e:
        logger.error(f"Error during demonstration: {e}")
        raise
    finally:
        # Database file is preserved in ./db/arxiv.dev.db for inspection
        logger.info(f"Database file saved at: {db_path}")


if __name__ == "__main__":
    main()
