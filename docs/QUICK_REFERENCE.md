# TheArk Quick Reference

Quick reference for common development tasks and commands.

## Development Commands

### Setup & Installation

```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .

# Activate virtual environment
source .venv/bin/activate
```

### Code Quality

```bash
# Format code
uv run black .

# Type checking
uv run mypy core/ crawler/ --strict

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=core --cov=crawler --cov-report=term-missing

# Run all quality checks
uv run black . && uv run mypy core/ crawler/ --strict && uv run pytest
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_core.py

# Run with verbose output
uv run pytest -v

# Run tests matching pattern
uv run pytest -k "test_logging"

# Run tests in parallel
uv run pytest -n auto
```

## Code Snippets

### Logging

```python
from core import get_logger, setup_logging

# Setup logging
setup_logging(level=logging.INFO, enable_file_logging=True)

# Get logger
logger = get_logger(__name__)

# Usage
logger.info("Processing started")
logger.debug("Processing item: %s", item_id)
logger.error("Failed to process: %s", error, exc_info=True)
```

### Type Hints

```python
# Modern type hints
def process_data(items: list[str]) -> dict[str, int]:
    """Process items and return counts."""
    return {item: items.count(item) for item in set(items)}

# Optional types
def get_config(key: str, default: str | None = None) -> str | None:
    """Get configuration value."""
    pass

# Dataclasses
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str
    active: bool = True
```

### Path Handling

```python
from pathlib import Path

# Create paths
log_dir = Path("logs")
log_file = log_dir / "app.log"

# Check existence
if log_file.exists():
    content = log_file.read_text()

# Create directories
log_dir.mkdir(parents=True, exist_ok=True)
```

### Testing

```python
import pytest
from unittest.mock import patch

def test_function():
    """Test function behavior."""
    result = function_under_test()
    assert result == expected_value

@patch("module.function")
def test_with_mock(mock_function):
    """Test with mocked dependency."""
    mock_function.return_value = "mocked"
    result = function_under_test()
    assert result == "mocked"
```

## Git Workflow

### Branch Management

```bash
# Create feature branch
git checkout -b feature/your-feature

# Switch to main
git checkout main

# Update main
git pull origin main

# Merge feature branch
git merge feature/your-feature
```

### Commit Messages

```bash
# Feature
git commit -m "feat: add new logging feature"

# Bug fix
git commit -m "fix: resolve connection timeout issue"

# Documentation
git commit -m "docs: update developer guide"

# Refactoring
git commit -m "refactor: simplify logging configuration"
```

## Common Issues & Solutions

### Import Errors

```bash
# Problem: Module not found
# Solution: Install in development mode
uv pip install -e .
```

### Type Checking Errors

```python
# Problem: Missing return type
def process_data(items):  # ❌
    return result

# Solution: Add return type
def process_data(items) -> dict[str, int]:  # ✅
    return result
```

### Test Failures

```bash
# Problem: Tests failing
# Solution: Check virtual environment
source .venv/bin/activate
uv sync
uv run pytest
```

### Formatting Issues

```bash
# Problem: Code not formatted
# Solution: Run black
uv run black .
```

## IDE Configuration

### VS Code / Cursor Settings

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### PyCharm Settings

- **Project Interpreter**: `.venv/bin/python`
- **Code Style**: Black formatter
- **Type Checking**: MyPy enabled
- **Auto-import**: Enable organize imports

## Environment Variables

```bash
# Development
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export LOG_LEVEL=DEBUG

# Production
export LOG_LEVEL=INFO
export LOG_DIR=/var/log/theark
```

## Useful Aliases

Add these to your `.bashrc` or `.zshrc`:

```bash
# TheArk development aliases
alias theark-test="uv run pytest"
alias theark-type="uv run mypy core/ crawler/ --strict"
alias theark-format="uv run black ."
alias theark-check="uv run black . && uv run mypy core/ crawler/ --strict && uv run pytest"
alias theark-sync="uv sync"
```

---

**Last Updated**: December 2024  
**See Also**: [Developer Guide](DEVELOPER_GUIDE.md)
