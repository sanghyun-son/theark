#!/bin/bash

# Test script for theark project
# Usage:
#   ./test.sh              # Run fast tests only
#   ./test.sh --all        # Run all tests (including slow)
#   ./test.sh --slow       # Run slow tests only
#   ./test.sh --verbose    # Run fast tests with verbose output
#   ./test.sh --logs       # Run fast tests with application logs
#   ./test.sh --all --verbose  # Run all tests with verbose output
#   ./test.sh [TARGET]     # Run specific test target (predefined or directory)
#   ./test.sh [TARGET] --verbose  # Run specific target with verbose output
#   ./test.sh tests/core/  # Run tests in specific directory
#   ./test.sh tests/crawler/database/  # Run tests in subdirectory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [TARGET]"
    echo ""
    echo "Options:"
echo "  --all       Run all tests (including slow tests)"
echo "  --slow      Run only slow tests"
echo "  --verbose   Run with verbose output (test details)"
echo "  --logs      Run with application logs (--log-cli-level=INFO)"
echo "  --help      Show this help message"
    echo ""
    echo "Targets:"
echo "  core        Run core module tests"
echo "  database    Run database module tests"
echo "  arxiv       Run arXiv module tests"
echo "  crawler     Run crawler module tests"
echo "  api         Run API module tests"
echo ""
echo "Directory Examples:"
echo "  tests/core/              # Run tests in core directory"
echo "  tests/crawler/database/  # Run tests in database subdirectory"
echo "  tests/crawler/arxiv/     # Run tests in arxiv subdirectory"
echo "  tests/core/test_log.py   # Run specific test file"
    echo ""
    echo "Examples:"
echo "  $0                    # Run fast tests only"
echo "  $0 --all              # Run all tests"
echo "  $0 --verbose          # Run fast tests with verbose output"
echo "  $0 --logs             # Run fast tests with application logs"
echo "  $0 core               # Run core tests only"
echo "  $0 database --verbose # Run database tests with verbose output"
echo "  $0 tests/core/        # Run tests in core directory"
echo "  $0 tests/crawler/database/ --verbose  # Run database tests with verbose output"
echo "  $0 --slow             # Run slow tests only"
}

# Parse arguments
RUN_ALL=false
RUN_SLOW=false
VERBOSE=false
LOGS=false
TARGET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            RUN_ALL=true
            shift
            ;;
        --slow)
            RUN_SLOW=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$TARGET" ]]; then
                TARGET="$1"
            else
                print_error "Multiple targets specified: $TARGET and $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="uv run pytest"

# Add verbose flag if requested
if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add logs flag if requested
if [[ "$LOGS" == true ]]; then
    PYTEST_CMD="$PYTEST_CMD --log-cli-level=INFO"
fi

# Determine what to run
if [[ "$RUN_SLOW" == true ]]; then
    # Run only slow tests
    print_info "Running slow tests only..."
    $PYTEST_CMD -m slow
elif [[ "$RUN_ALL" == true ]]; then
    # Run all tests
    print_info "Running all tests (including slow tests)..."
    $PYTEST_CMD tests/
elif [[ -n "$TARGET" ]]; then
    # Check if it's a predefined target or a directory path
    case $TARGET in
        core)
            print_info "Running core module tests..."
            $PYTEST_CMD tests/core/
            ;;
        database)
            print_info "Running database module tests..."
            $PYTEST_CMD tests/crawler/database/
            ;;
        arxiv)
            print_info "Running arXiv module tests..."
            $PYTEST_CMD tests/crawler/arxiv/
            ;;
        crawler)
            print_info "Running crawler module tests..."
            $PYTEST_CMD tests/crawler/
            ;;
        api)
            print_info "Running API module tests..."
            $PYTEST_CMD tests/api/
            ;;
        *)
            # Check if it's a valid directory or file path
            if [[ -d "$TARGET" ]] || [[ -f "$TARGET" ]]; then
                print_info "Running tests in: $TARGET"
                $PYTEST_CMD "$TARGET"
            else
                print_error "Unknown target: $TARGET"
                echo "Available predefined targets: core, database, arxiv, crawler, api"
                echo "Or use directory paths like: tests/core/, tests/crawler/database/"
                exit 1
            fi
            ;;
    esac
else
    # Run fast tests only (default)
    print_info "Running fast tests only (excluding slow tests)..."
    $PYTEST_CMD -m "not slow" tests/
fi

# Check if tests passed
if [[ $? -eq 0 ]]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed!"
    exit 1
fi
