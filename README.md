# TheArk

A web crawling and data processing system.

## Installation

```bash
# Install in development mode
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
```

## Development

This project uses:
- **Python**: >=3.11
- **Type Checking**: `mypy --strict`
- **Formatting**: `black`
- **Testing**: `pytest`
- **Dependency Management**: `uv`

### Quick Start

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### Documentation

- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Comprehensive development guidelines
- **[Quick Reference](docs/QUICK_REFERENCE.md)**: Common commands and code snippets

### Code Quality

```bash
# Format code
uv run black .

# Type checking
uv run mypy core/ crawler/

# Run tests
uv run pytest

# Run tests with coverage (when needed)
uv run pytest --cov=core --cov=crawler --cov-report=term-missing
```

## Features

- **Colored Logging**: Beautiful colored log output using `colorlog`
- **Type Safety**: Full type checking with `mypy --strict`
- **Code Quality**: Automated formatting with `black` and linting with `ruff`
- **Testing**: Comprehensive test suite with `pytest` and coverage reporting

## Project Structure

```
theark/
├── core/                    # Core functionality (logging, etc.)
├── crawler/                 # Web crawling components
├── tests/                   # Test suite
├── docs/                    # Documentation
│   ├── DEVELOPER_GUIDE.md   # Development guidelines
│   └── QUICK_REFERENCE.md   # Quick reference
└── pyproject.toml          # Project configuration
```

## License

MIT License
