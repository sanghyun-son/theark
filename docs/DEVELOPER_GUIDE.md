# TheArk Developer Guide

This guide provides comprehensive information for developers working on the TheArk project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Logging System](#logging-system)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Quality](#code-quality)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

- **Python**: >=3.11
- **uv**: Modern Python package manager
- **Git**: Version control

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd theark

# Install uv if not already installed
pip install uv

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Development Environment

### Virtual Environment

The project uses `uv` for dependency management. The virtual environment is automatically created in `.venv/`.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Or use uv run (recommended)
uv run python your_script.py
```

### IDE Configuration

#### VS Code / Cursor

Recommended extensions:
- Python
- Pylance
- Black Formatter
- MyPy Type Checker

#### PyCharm

- Set the project interpreter to `.venv/bin/python`
- Enable type checking with MyPy
- Configure Black as the code formatter

## Coding Standards

### Python Style Guide

We follow **PEP8**, **PEP484**, **PEP604**, and **PEP257** with the following specific rules:

#### Type Hints

- Use modern type hints: `str | None` instead of `Optional[str]`
- Use built-in generics: `list[str]` instead of `List[str]`
- Always provide return types for functions
- Use `@dataclass` for structured data

```python
# ✅ Good
def process_data(items: list[str]) -> dict[str, int]:
    """Process a list of items and return counts."""
    return {item: items.count(item) for item in set(items)}

# ❌ Bad
def process_data(items):  # No type hints
    return {item: items.count(item) for item in set(items)}
```

#### Naming Conventions

- **Variables & functions**: `snake_case`
- **Classes & exceptions**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Modules**: `snake_case`

#### Path Handling

- Use `pathlib.Path` instead of `os.path`
- Avoid string concatenation with `/`

```python
# ✅ Good
from pathlib import Path
log_file = Path("logs") / "app.log"

# ❌ Bad
import os
log_file = os.path.join("logs", "app.log")
```

#### Logging

- Use the project's logging system: `from core import get_logger`
- Create loggers with `__name__`: `logger = get_logger(__name__)`
- Avoid `print()` statements

```python
from core import get_logger

logger = get_logger(__name__)

def process_item(item: str) -> None:
    logger.info("Processing item: %s", item)
    # ... processing logic
```

### Code Organization

#### Functions

- Keep functions small and focused (≤40 lines)
- Single responsibility principle
- Explicit arguments and return types
- Raise precise exceptions (`ValueError`, `KeyError`, not bare `Exception`)

#### Classes

- Use `@dataclass` for simple data structures
- Use Pydantic models for API input/output validation
- Avoid premature abstraction

#### Imports

Order imports as follows:
1. Standard library
2. Third-party packages
3. Project modules

```python
import logging
from pathlib import Path
from typing import Any

import colorlog
import pytest

from core import get_logger, setup_logging
```

## Testing Guidelines

### Test Structure

- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- **Test files**: `test_*.py`
- **Test classes**: `Test*`
- **Test functions**: `test_*`

### Writing Tests

```python
"""Unit tests for module functionality."""

import pytest
from unittest.mock import patch

from core import get_logger, setup_logging


class TestLogging:
    """Test logging functionality."""

    def test_setup_logging_defaults(self) -> None:
        """Test setup_logging with default parameters."""
        setup_logging()
        # ... test logic

    @patch("sys.stdout")
    def test_logging_output(self, mock_stdout) -> None:
        """Test that logging outputs to stdout."""
        # ... test logic
```

### Test Best Practices

- Test normal flow, edge cases, and error handling
- Use descriptive test names
- Keep tests focused and independent
- Use fixtures for setup/teardown
- Prefer real objects over mocks when feasible

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=core --cov=crawler --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_core.py

# Run with verbose output
uv run pytest -v
```

## Logging System

### Overview

The project uses a centralized logging system with the following features:

- **Colored console output** for development
- **File logging** with rotation for production
- **Structured format** with timestamps and context
- **Extensible design** for future Loki integration

### Usage

```python
from core import get_logger, setup_logging

# Setup logging (usually done once at startup)
setup_logging(level=logging.INFO, enable_file_logging=True)

# Get a logger for your module
logger = get_logger(__name__)

# Use the logger
logger.info("Application started")
logger.debug("Processing item: %s", item_id)
logger.error("Failed to process item: %s", item_id, exc_info=True)
```

### Configuration Options

```python
# Development setup
setup_logging(
    level=logging.DEBUG,
    use_colors=True,
    enable_file_logging=False
)

# Production setup
setup_logging(
    level=logging.INFO,
    use_colors=False,
    enable_file_logging=True,
    log_dir=Path("/var/log/theark")
)

# Test setup
setup_logging(
    level=logging.DEBUG,
    enable_file_logging=True,
    is_test_env=True
)
```

### Log Format

The default log format includes:
- Timestamp: `%m-%d %H:%M:%S`
- Log level: Right-aligned 8 characters
- Message: The actual log message
- Context: `(module@filename:line_number)`

Example output:
```
12-15 14:30:25     INFO Application started (main@app.py:42)
12-15 14:30:26    DEBUG Processing item: 12345 (processor@worker.py:15)
```

## Project Structure

```
theark/
├── core/                    # Core functionality
│   ├── __init__.py
│   └── log.py              # Logging system
├── crawler/                 # Web crawling components
│   └── __init__.py
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest configuration
├── docs/                    # Documentation
│   └── DEVELOPER_GUIDE.md  # This file
├── logs/                    # Log files (gitignored)
├── pyproject.toml          # Project configuration
├── uv.lock                 # Dependency lock file
└── README.md               # Project overview
```

## Development Workflow

### 1. Feature Development

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... coding ...

# Run quality checks
uv run black .
uv run mypy core/ crawler/ --strict
uv run pytest

# Commit your changes
git add .
git commit -m "feat: add new feature description"
```

### 2. Code Review Process

1. **Self-review**: Run all quality checks before submitting
2. **Peer review**: Request review from team members
3. **Address feedback**: Make necessary changes
4. **Merge**: Once approved, merge to main branch

### 3. Commit Message Format

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

Examples:
```
feat(logging): add Loki integration support
fix(crawler): handle connection timeout errors
docs: update developer guide with new guidelines
refactor(core): simplify logging configuration
```

## Code Quality

### Automated Checks

```bash
# Format code
uv run black .

# Type checking
uv run mypy core/ crawler/ --strict

# Linting (if using ruff)
uv run ruff check .

# Run tests
uv run pytest

# Check all at once
uv run black . && uv run mypy core/ crawler/ --strict && uv run pytest
```

### Pre-commit Hooks

Consider setting up pre-commit hooks to automatically run quality checks:

```bash
# Install pre-commit
uv add --dev pre-commit

# Create .pre-commit-config.yaml
# Run pre-commit install
```

### Code Review Checklist

Before submitting code for review, ensure:

- [ ] Code follows style guidelines
- [ ] Type hints are complete and correct
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] No unused imports or variables
- [ ] Error handling is appropriate
- [ ] Logging is used instead of print statements

## Troubleshooting

### Common Issues

#### Type Checking Errors

```bash
# If you get mypy errors, check:
# 1. All functions have return type annotations
# 2. All parameters have type hints
# 3. Variables are properly typed
```

#### Test Failures

```bash
# If tests fail:
# 1. Check if you're in the right virtual environment
# 2. Ensure dependencies are installed: uv sync
# 3. Check test logs for specific error messages
```

#### Import Errors

```bash
# If you get import errors:
# 1. Ensure you're using absolute imports
# 2. Check that the package is installed: uv pip install -e .
# 3. Verify the module structure
```

### Getting Help

1. **Check this guide** for common solutions
2. **Search existing issues** in the repository
3. **Ask in team chat** for quick questions
4. **Create an issue** for bugs or feature requests
5. **Request code review** for implementation help

## Contributing

### Before Contributing

1. Read this developer guide thoroughly
2. Understand the project structure and coding standards
3. Set up your development environment
4. Familiarize yourself with the existing codebase

### Contribution Process

1. **Fork the repository** (if external contributor)
2. **Create a feature branch**
3. **Make your changes** following the coding standards
4. **Write tests** for new functionality
5. **Update documentation** as needed
6. **Run quality checks** before submitting
7. **Submit a pull request** with clear description
8. **Address review feedback** promptly

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's coding standards
- Communicate clearly and professionally

---

**Last Updated**: December 2024  
**Maintainer**: TheArk Development Team
