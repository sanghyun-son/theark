# TheArk

A web crawling and data processing system.

## Installation

```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Development

This project uses:
- **Python**: >=3.11
- **Type Checking**: `mypy --strict`
- **Formatting**: `black`
- **Testing**: `pytest`
- **Dependency Management**: `uv`

### Setup

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### Code Quality

```bash
# Format code
black .

# Type checking
mypy core/ crawler/

# Run tests
pytest

# Run tests with coverage
pytest --cov=core --cov=crawler
```

## Project Structure

```
theark/
├── core/           # Core functionality
├── crawler/        # Web crawling components
├── tests/          # Test suite
└── pyproject.toml  # Project configuration
```

## License

MIT License
