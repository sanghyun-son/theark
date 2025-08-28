#!/bin/bash

# TheArk Code Quality Check Script
# Performs type checking, linting, and formatting checks

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
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

# Source directories to check
SOURCE_DIRS="core/ api/"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a command with proper output handling
run_command() {
    local tool_name="$1"
    local command="$2"
    local action="$3"
    
    echo "[$tool_name]"
    print_status "$action..."
    
    if $VERBOSE; then
        if eval "$command"; then
            print_success "$action completed successfully"
        else
            print_error "$action failed"
            return 1
        fi
    else
        if eval "$command" >/dev/null 2>&1; then
            print_success "$action completed successfully"
        else
            print_error "$action failed"
            return 1
        fi
    fi
}

# Check if uv is available
if ! command_exists uv; then
    print_error "uv is not installed. Please install uv first."
    print_status "Install with: pip install uv"
    exit 1
fi

print_status "Starting code quality checks..."

# Parse command line arguments
CHECK_TYPE="all"
VERBOSE=true
FIX_MODE=true  # Default to fix mode

while [[ $# -gt 0 ]]; do
    case $1 in
        --typecheck-only)
            CHECK_TYPE="typecheck"
            shift
            ;;
        --lint-only)
            CHECK_TYPE="lint"
            shift
            ;;
        --format-only)
            CHECK_TYPE="format"
            shift
            ;;
        --quiet)
            VERBOSE=false
            shift
            ;;
        --no-fix)
            FIX_MODE=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --typecheck-only    Run only type checking"
            echo "  --lint-only         Run only linting"
            echo "  --format-only       Run only formatting checks"
            echo "  --quiet             Quiet output (default is verbose)"
            echo "  --no-fix            Disable auto-fixing (default is auto-fix)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Default behavior: Run all checks with verbose output and auto-fix enabled"
            echo "Use --no-fix to disable auto-fixing and only check for issues"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

run_linting() {
    if $FIX_MODE; then
        run_command "ruff" "uv run ruff check --fix $SOURCE_DIRS" "Fixing linting issues"
    else
        run_command "ruff" "uv run ruff check $SOURCE_DIRS" "Checking linting issues"
    fi
}

run_formatting() {
    # Black - can be auto-fixed
    if $FIX_MODE; then
        run_command "black" "uv run black $SOURCE_DIRS" "Fixing code formatting"
    else
        run_command "black" "uv run black --check $SOURCE_DIRS" "Checking code formatting"
    fi
}

run_typecheck() {
    run_command "mypy" "uv run mypy $SOURCE_DIRS --ignore-missing-imports --strict" "Running type checking"
}

# Main execution
case $CHECK_TYPE in
    "typecheck")
        run_typecheck
        ;;
    "lint")
        run_linting
        ;;
    "format")
        run_formatting
        ;;
    "all")
        print_status "Running all code quality checks..."
        echo ""
        
        if ! run_linting; then
            print_error "Linting checks failed!"
            exit 1
        fi
        echo ""
        
        # Run formatting (black)
        if ! run_formatting; then
            print_error "Formatting checks failed!"
            exit 1
        fi
        echo ""
        
        # Run type checking last
        if ! run_typecheck; then
            print_error "Type checking failed!"
            exit 1
        fi
        echo ""
        
        print_success "All code quality checks passed! 🎉"
        ;;
    *)
        print_error "Unknown check type: $CHECK_TYPE"
        exit 1
        ;;
esac
