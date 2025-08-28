# Scripts

This directory contains utility scripts for development, testing, and running the application.

## Directory Structure

```
scripts/
├── dev/          # Development utilities
│   ├── test.sh   # Test runner
│   └── check.sh  # Code quality checks
├── run/          # Application runners
│   └── start.sh  # Start the application
└── README.md     # This file
```

## Development Scripts (`dev/`)

### `test.sh` - Test Runner

Run tests with various options:

```bash
# Run all tests
./scripts/dev/test.sh

# Run integration tests only
./scripts/dev/test.sh --integration

# Run unit tests only
./scripts/dev/test.sh --unit

# Run specific test directories
./scripts/dev/test.sh tests/core/ tests/api/

# Run with logging
./scripts/dev/test.sh --log-debug
./scripts/dev/test.sh --log-info

# Run with verbose output
./scripts/dev/test.sh --verbose
```

### `check.sh` - Code Quality Checks

Run code quality checks and formatting:

```bash
# Run all checks with auto-fix (default)
./scripts/dev/check.sh

# Run checks without auto-fixing
./scripts/dev/check.sh --no-fix

# Run specific checks
./scripts/dev/check.sh --lint-only
./scripts/dev/check.sh --format-only
./scripts/dev/check.sh --typecheck-only
```

## Application Scripts (`run/`)

### `start.sh` - Application Runner

Start the TheArk application:

```bash
# Start in development mode
./scripts/run/start.sh

# Start with specific options
./scripts/run/start.sh --host 0.0.0.0 --port 8000
```

## Quick Aliases

For convenience, you can create aliases in your shell profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias test="./scripts/dev/test.sh"
alias check="./scripts/dev/check.sh"
alias start="./scripts/run/start.sh"
```

## Contributing

When adding new scripts:

1. Place them in the appropriate subdirectory (`dev/`, `run/`, etc.)
2. Make them executable: `chmod +x scripts/path/to/script.sh`
3. Update this README with usage documentation
4. Follow the existing script patterns and conventions
