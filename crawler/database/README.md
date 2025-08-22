# Database Module

This module provides a comprehensive database system for the arXiv crawler using the Strategy pattern to support multiple database backends.

## Architecture

The database system follows a layered architecture:

1. **Database Manager** (Strategy Pattern): Abstract interface for different database backends
2. **Models** (Pydantic): Type-safe data models with validation
3. **Repository Layer**: High-level operations for each entity
4. **SQLite Implementation**: Current implementation using SQLite

## Components

### Database Manager (`base.py`)

Abstract base class defining the interface for database operations:

- Connection management
- Query execution (single and batch)
- Data fetching (single row and multiple rows)
- Table creation
- Context manager support

### SQLite Manager (`sqlite_manager.py`)

SQLite implementation of the database manager with:

- WAL mode support (disabled for testing)
- Foreign key constraints
- Optimized performance settings
- Full-text search support (FTS5, currently disabled for testing)

### Models (`models.py`)

Pydantic models for type safety and validation:

- `Paper`: arXiv paper entity
- `Summary`: Paper summaries with different styles
- `AppUser`: Application users
- `UserInterest`: User interests and preferences
- `UserStar`: User bookmarks/favorites
- `FeedItem`: Daily feed items
- `CrawlEvent`: Crawling event logs

### Repository Layer (`repository.py`)

High-level operations for each entity:

- `PaperRepository`: Paper CRUD and search operations
- `SummaryRepository`: Summary management
- `UserRepository`: User and interest management
- `FeedRepository`: Feed item operations
- `CrawlEventRepository`: Crawling event logging

## Database Schema

### Core Tables

1. **paper**: Main paper entity
   - `paper_id` (PK)
   - `arxiv_id` (unique)
   - `title`, `abstract`, `authors`
   - `primary_category`, `categories`
   - `url_abs`, `url_pdf`
   - `published_at`, `updated_at`

2. **summary**: Paper summaries
   - `summary_id` (PK)
   - `paper_id` (FK)
   - `version`, `overview`, `motivation`, `method`, `result`, `conclusion`
   - `language` (Korean/English), `interests`, `relevance` (0-10)
   - `model` (LLM used)

3. **app_user**: Application users
   - `user_id` (PK)
   - `email` (unique)
   - `display_name`

4. **user_interest**: User preferences
   - `user_id` (FK)
   - `kind` (category/keyword/author)
   - `value`, `weight`

5. **user_star**: User bookmarks
   - `user_id` (FK)
   - `paper_id` (FK)
   - `note`, `created_at`

6. **feed_item**: Daily feed items
   - `feed_item_id` (PK)
   - `user_id` (FK)
   - `paper_id` (FK)
   - `score`, `feed_date`

7. **crawl_event**: Crawling logs
   - `event_id` (PK)
   - `arxiv_id`
   - `event_type` (FOUND/UPDATED/SKIPPED/ERROR)
   - `detail`, `created_at`

### Indexes

- `idx_paper_published_at`: Recent papers
- `idx_paper_primary_category`: Category filtering
- `idx_user_star_user`: User favorites
- `idx_summary_paper`: Paper summaries by language

### Full-Text Search

FTS5 virtual table for `paper_fts` with triggers for automatic synchronization (currently disabled for testing).

## Usage

### Basic Setup

```python
from crawler.database import SQLiteManager, PaperRepository, setup_database_environment

# Setup database environment (development, testing, production)
config = setup_database_environment("development")
db_path = config.database_path

# Initialize database
with SQLiteManager(db_path) as db_manager:
    # Create tables
    db_manager.create_tables()
    
    # Create repositories
    paper_repo = PaperRepository(db_manager)
    
    # Use repositories
    papers = paper_repo.get_recent_papers(limit=10)
```

### Environment Configuration

The database system supports different environments:

- **Production**: Uses `./db/arxiv.db`
- **Development**: Uses `./db/arxiv.dev.db`
- **Testing**: Uses temporary files in `/tmp`

```python
from crawler.database import DatabaseConfig

# Development environment
config = DatabaseConfig("development")
db_path = config.database_path  # ./db/arxiv.dev.db

# Testing environment
config = DatabaseConfig("testing")
db_path = config.database_path  # /tmp/tmpXXXXXX.db

# Production environment
config = DatabaseConfig("production")
db_path = config.database_path  # ./db/arxiv.db
```

### Paper Operations

```python
from crawler.database.models import Paper

# Create a paper
paper = Paper(
    arxiv_id="2101.00001",
    title="Attention Is All You Need",
    abstract="The dominant sequence transduction models...",
    primary_category="cs.CL",
    categories="cs.CL,cs.LG",
    authors="Ashish Vaswani;Noam Shazeer",
    url_abs="https://arxiv.org/abs/2101.00001",
    published_at="2021-01-01T00:00:00Z",
    updated_at="2021-01-01T00:00:00Z",
)

paper_id = paper_repo.create(paper)
retrieved_paper = paper_repo.get_by_arxiv_id("2101.00001")
```

### Summary Operations

```python
from crawler.database.models import Summary

# Create a summary
summary = Summary(
    paper_id=1,
    version=1,
    overview="This paper presents a novel approach",
    motivation="Current methods have limitations",
    method="We propose a new neural network",
    result="Our method achieves state-of-the-art results",
    conclusion="This work opens new research directions",
    language="English",
    interests="machine learning,neural networks,nlp",
    relevance=8,
    model="gpt-4"
)
summary_id = summary_repo.create(summary)

# Get summary by paper and language
summary = summary_repo.get_by_paper_and_language(paper_id=1, language="English")
```

### Search Operations

```python
# Search by keywords
results = paper_repo.search_by_keywords("transformer", limit=20)

# Get recent papers
recent = paper_repo.get_recent_papers(limit=100)
```

### User Management

```python
from crawler.database.models import AppUser, UserInterest, UserStar

# Create user
user = AppUser(email="user@example.com", display_name="Test User")
user_id = user_repo.create_user(user)

# Add interests
interest = UserInterest(
    user_id=user_id,
    kind="category",
    value="cs.CL",
    weight=2.0
)
user_repo.add_interest(interest)

# Add bookmark
star = UserStar(
    user_id=user_id,
    paper_id=paper_id,
    note="Interesting paper"
)
user_repo.add_star(star)
```

### Crawl Event Logging

```python
from crawler.database.models import CrawlEvent

event = CrawlEvent(
    arxiv_id="2101.00001",
    event_type="FOUND",
    detail="Paper found during crawl"
)
event_repo.log_event(event)
```

## Testing

The module includes comprehensive tests:

- **Model validation tests**: Ensure data integrity
- **Database operation tests**: CRUD operations and constraints
- **Repository tests**: High-level operations
- **Integration tests**: End-to-end workflows

Run tests with:

```bash
uv run pytest tests/unit/test_database_*.py -v
```

## Future Extensions

The Strategy pattern allows easy extension to other databases:

1. **PostgreSQL Manager**: For production use
2. **Cloud Database Manager**: For cloud deployments
3. **In-Memory Manager**: For testing and caching

## Database Directory Structure

```
./db/                     # Development and Production
├── arxiv.db              # Production database file
├── arxiv.dev.db          # Development database file
├── database.log          # Database operation logs
└── backups/              # Database backups
    ├── backup_20231201_143022.db
    └── custom_backup.db
```

## Performance Considerations

- SQLite with DELETE journal mode for testing
- WAL mode for production (better concurrency)
- Indexed queries for common operations
- Batch operations for bulk inserts
- Connection pooling for high concurrency

## Error Handling

- Comprehensive error logging using `core.log`
- Graceful handling of database errors
- Transaction rollback on failures
- Validation errors with descriptive messages
