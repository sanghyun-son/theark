#!/bin/bash

# Test script for theark project
# Usage:
#   ./test.sh                    # Run all tests
#   ./test.sh --integration      # Run integration tests only
#   ./test.sh --unit             # Run unit tests only (excluding integration)
#   ./test.sh --verbose          # Run with verbose output
#   ./test.sh --log-info         # Run with INFO level logging
#   ./test.sh --log-debug        # Run with DEBUG level logging
#   ./test.sh [TARGET1] [TARGET2] ...  # Run specific test directories
#   ./test.sh tests/core/ tests/api/   # Run multiple specific directories

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
    echo "Usage: $0 [OPTIONS] [TARGET1] [TARGET2] ..."
    echo ""
    echo "Options:"
    echo "  --integration  Run integration tests only (tests/integration/)"
    echo "  --unit         Run unit tests only (tests/* except tests/integration/)"
    echo "  --verbose      Run with verbose output (test details)"
    echo "  --log-info     Run with INFO level logging (--log-cli-level=INFO)"
    echo "  --log-debug    Run with DEBUG level logging (--log-cli-level=DEBUG)"
    echo "  --help         Show this help message"
    echo ""
    echo "Targets:"
    echo "  Multiple test directories can be specified"
    echo "  Examples:"
    echo "    tests/core/              # Run tests in core directory"
    echo "    tests/api/               # Run tests in api directory"
    echo "    tests/core/database/     # Run tests in database subdirectory"
    echo "    tests/core/test_log.py   # Run specific test file"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 --integration                      # Run integration tests only"
    echo "  $0 --unit                            # Run unit tests only"
    echo "  $0 --verbose                         # Run all tests with verbose output"
    echo "  $0 --log-info                        # Run all tests with INFO level logging"
    echo "  $0 --log-debug                       # Run all tests with DEBUG level logging"
    echo "  $0 tests/core/                       # Run tests in core directory"
    echo "  $0 tests/core/ tests/api/            # Run tests in multiple directories"
    echo "  $0 tests/core/database/ --verbose    # Run database tests with verbose output"
}

# Parse arguments
RUN_INTEGRATION=false
RUN_UNIT=false
VERBOSE=false
LOG_LEVEL=""
TARGETS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --unit)
            RUN_UNIT=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --log-info)
            LOG_LEVEL="INFO"
            shift
            ;;
        --log-debug)
            LOG_LEVEL="DEBUG"
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
            TARGETS+=("$1")
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

# Add log level flag if requested
if [[ -n "$LOG_LEVEL" ]]; then
    PYTEST_CMD="$PYTEST_CMD --log-cli-level=$LOG_LEVEL --capture=no"
fi

# Determine what to run
if [[ "$RUN_INTEGRATION" == true ]]; then
    # Run integration tests only
    print_info "Running integration tests only..."
    $PYTEST_CMD tests/integration/
elif [[ "$RUN_UNIT" == true ]]; then
    # Run unit tests only (excluding integration)
    print_info "Running unit tests only (excluding integration)..."
    $PYTEST_CMD tests/core/ tests/api/
elif [[ ${#TARGETS[@]} -gt 0 ]]; then
    # Run specific targets
    print_info "Running tests in specified targets: ${TARGETS[*]}"
    $PYTEST_CMD "${TARGETS[@]}"
else
    # Run all tests (default)
    print_info "Running all tests..."
    $PYTEST_CMD tests/
fi

# Check if tests passed
if [[ $? -eq 0 ]]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed!"
    exit 1
fi
