# TheArk

[![CI](https://github.com/sanghyun-son/theark/actions/workflows/ci.yml/badge.svg)](https://github.com/sanghyun-son/theark/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/sanghyun-son/theark/branch/main/graph/badge.svg)](https://codecov.io/gh/sanghyun-son/theark)
[![Python 3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A web crawling and data processing system focused on arXiv paper crawling and analysis.

## 🚀 Quick Start

```bash
# Install uv if not already installed
pip install uv

# Install dependencies and setup development environment
uv sync
uv pip install -e .

# Run tests
./test.sh
```

## 📋 Project Status

### ✅ Completed Components

#### **Core Module (`core/`)**
- **Logging System**: Colored logging with file rotation and test environment support
- **Rate Limiter**: Async rate limiter with iteration support for batch processing
  - Configurable requests per second
  - Async context manager support
  - Iteration methods: `iterate()`, `iterate_with_results()`, `iterate_concurrent()`

#### **Database Module (`crawler/database/`)**
- **SQLite Manager**: Strategy pattern implementation for database management
- **Pydantic Models**: Type-safe data models for all entities
- **Repository Pattern**: Clean abstraction layer for database operations
- **Environment Configuration**: Development, testing, and production database paths
- **Summary Model**: Structured summaries with overview, motivation, method, result, conclusion

#### **arXiv Module (`crawler/arxiv/`)**
- **Custom Exceptions**: Comprehensive error handling for arXiv operations
- **ArXivClient**: Single paper fetching with flexible input formats
  - Supports arXiv ID, abstract URLs, and PDF URLs
  - Built-in rate limiting (1 request/second)
  - Proper error handling and async context management
  - Real arXiv API integration
- **ArXivCrawler**: Background event loop crawler with periodic fetching
  - Background event loop for continuous crawling
  - Single paper crawling with database integration
  - Placeholder methods for recent/monthly papers (future implementation)
  - Configurable rate limiting and error handling
  - Callback support for paper events and errors
  - Status monitoring and statistics
- **Mock Server**: `pytest-httpserver` based mock for reliable testing

#### **Testing Infrastructure**
- **Test Organization**: Mirror source directory structure
- **Mock arXiv Server**: Realistic XML responses for testing
- **Test Script**: `./test.sh` with multiple testing modes
- **Slow Test Marking**: Rate limiter tests marked as slow for faster development

### ✅ Completed
- **ArXivParser**: XML/Atom feed parser for paper metadata extraction ✅

## 🛠️ Development

### Testing

```bash
# Fast tests only (default)
./test.sh

# All tests (including slow tests)
./test.sh --all

# Slow tests only
./test.sh --slow

# Verbose output (test details)
./test.sh --verbose

# Application logs (internal behavior)
./test.sh --logs

# Predefined module tests
./test.sh core
./test.sh database
./test.sh arxiv

# Directory-style targeting
./test.sh tests/core/
./test.sh tests/crawler/database/
./test.sh tests/core/test_log.py

# Combined options
./test.sh core --verbose
./test.sh tests/crawler/database/ --logs
./test.sh --all --verbose
```

### Code Quality

```bash
# Format code
uv run black .

# Type checking
uv run mypy core/ crawler/

# Run tests with coverage
uv run pytest --cov=core --cov=crawler --cov-report=term-missing
```

## 🏗️ Architecture

### Core Principles
- **Database-First Deduplication**: Leverage database constraints for reliable deduplication
- **Strategy Pattern**: Extensible design for future cloud database support
- **Async/Await**: Modern Python async patterns for performance
- **Type Safety**: Full type checking with Pydantic models
- **Test-Driven**: Comprehensive test coverage with mock servers

### Key Design Decisions
- **Rate Limiting**: Core utility for arXiv compliance
- **Mock Testing**: Reliable testing without external dependencies
- **Environment Isolation**: Separate databases for dev/test/prod
- **Structured Summaries**: Rich metadata for paper analysis
- **Constants Management**: Centralized configuration and constants
- **Shared Test Data**: Reusable test fixtures and data

## 📁 Project Structure

```
theark/
├── core/                           # Core functionality
│   ├── log.py                     # Colored logging system
│   ├── rate_limiter.py            # Async rate limiter
│   └── __init__.py
├── crawler/                        # Crawling components
│   ├── database/                   # Database layer
│   │   ├── models.py              # Pydantic data models
│   │   ├── repository.py          # Repository pattern
│   │   ├── sqlite_manager.py      # SQLite implementation
│   │   ├── config.py              # Environment configuration
│   │   └── __init__.py
│   └── arxiv/                      # arXiv specific components
│       ├── exceptions.py          # Custom exceptions
│       ├── constants.py           # Centralized constants and configuration
│       ├── client.py              # ArXivClient for API integration
│       ├── parser.py              # ArXivParser for XML metadata extraction
│       ├── crawler.py             # ArXivCrawler with background loop
│       └── __init__.py
├── tests/                          # Test suite
│   ├── core/                      # Core module tests
│   ├── crawler/                   # Crawler module tests
│   │   ├── database/              # Database tests
│   │   └── arxiv/                 # arXiv tests
│   ├── conftest.py                # Shared fixtures & mock server
│   └── shared_test_data.py        # Shared test data and fixtures
├── examples/                       # Usage examples
│   ├── database_demo.py           # Database demonstration
│   ├── arxiv_client_demo.py       # ArXivClient demonstration
│   └── arxiv_crawler_demo.py      # ArXivCrawler demonstration
├── test.sh                        # Test runner script
└── pyproject.toml                 # Project configuration
```

## 🔧 Dependencies

### Core Dependencies
- **Python**: >=3.11
- **Pydantic**: Data validation and serialization
- **httpx**: Modern async HTTP client
- **colorlog**: Colored logging output

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-httpserver**: Mock HTTP server
- **mypy**: Type checking
- **black**: Code formatting
- **uv**: Fast dependency management

## 📊 Test Coverage

- **Total Tests**: 124 tests
- **Fast Tests**: 114 tests (~6.5s)
- **Slow Tests**: 10 tests (rate limiter tests)
- **Slow Tests**: 10 tests (~10s)
- **Modules Covered**: Core, Database, arXiv client & crawler
- **Mock Infrastructure**: Realistic arXiv API simulation

## 🎯 Next Steps

1. **ArXivParser**: XML/Atom feed parsing for paper metadata extraction
2. **Batch Processing**: Leverage rate limiter iteration methods for bulk operations
3. **Production Deployment**: Cloud database integration

## 📄 License

MIT License
