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
FIX_MODE=false

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
        --fix)
            FIX_MODE=true
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
            echo "  --fix               Fix formatting and import issues automatically"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Default behavior: Run all checks with verbose output"
            echo "With --fix: Automatically fix formatting and import issues"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to run formatting checks (black and isort)
run_formatting() {
    # Black - can be auto-fixed
    if $FIX_MODE; then
        run_command "black" "uv run black $SOURCE_DIRS" "Fixing code formatting"
    else
        run_command "black" "uv run black --check $SOURCE_DIRS" "Checking code formatting"
    fi
    
    # isort - can be auto-fixed
    if $FIX_MODE; then
        run_command "isort" "uv run isort $SOURCE_DIRS" "Fixing import sorting"
    else
        run_command "isort" "uv run isort --check-only $SOURCE_DIRS" "Checking import sorting"
    fi
}

# Function to run type checking
run_typecheck() {
    run_command "mypy" "uv run mypy $SOURCE_DIRS --ignore-missing-imports --strict" "Running type checking"
}

# Function to run linting
run_linting() {
    # flake8 - cannot be auto-fixed
    run_command "flake8" "uv run flake8 $SOURCE_DIRS" "Running linting"
    
    # bandit - security checks, always run
    echo "[bandit]"
    print_status "Running security checks..."
    if $VERBOSE; then
        uv run bandit -r $SOURCE_DIRS -f json -o bandit-report.json || true
    else
        uv run bandit -r $SOURCE_DIRS -f json -o bandit-report.json >/dev/null 2>&1 || true
    fi
    print_success "Security checks completed"
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
        
        # Run formatting first (can be auto-fixed)
        if ! run_formatting; then
            print_error "Formatting checks failed!"
            exit 1
        fi
        echo ""
        
        # Run type checking
        if ! run_typecheck; then
            print_error "Type checking failed!"
            exit 1
        fi
        echo ""
        
        # Run linting last (cannot be auto-fixed)
        if ! run_linting; then
            print_error "Linting failed!"
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
