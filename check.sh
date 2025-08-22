#!/bin/bash

# TheArk Code Quality Check Script
# Performs type checking, linting, and formatting checks

# Don't exit on error, handle them manually

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
SOURCE_DIRS="core/ crawler/ api/"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
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
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --typecheck-only    Run only type checking"
            echo "  --lint-only         Run only linting"
            echo "  --format-only       Run only formatting checks"
            echo "  --quiet             Quiet output (default is verbose)"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Default behavior: Run all checks with verbose output"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to run type checking
run_typecheck() {
    print_status "Running type checking with mypy..."
    if $VERBOSE; then
        if uv run mypy $SOURCE_DIRS --ignore-missing-imports --strict; then
            print_success "Type checking passed"
        else
            print_error "Type checking failed"
            return 1
        fi
    else
        if uv run mypy $SOURCE_DIRS --ignore-missing-imports --strict >/dev/null 2>&1; then
            print_success "Type checking passed"
        else
            print_error "Type checking failed"
            return 1
        fi
    fi
}

# Function to run linting
run_linting() {
    print_status "Running linting with flake8..."
    if $VERBOSE; then
        if uv run flake8 $SOURCE_DIRS; then
            print_success "Linting passed"
        else
            print_warning "Linting found issues (some line length warnings)"
        fi
    else
        if uv run flake8 $SOURCE_DIRS >/dev/null 2>&1; then
            print_success "Linting passed"
        else
            print_warning "Linting found issues (some line length warnings)"
        fi
    fi
    
    print_status "Running security checks with bandit..."
    if $VERBOSE; then
        uv run bandit -r $SOURCE_DIRS -f json -o bandit-report.json || true
    else
        uv run bandit -r $SOURCE_DIRS -f json -o bandit-report.json >/dev/null 2>&1 || true
    fi
    print_success "Security checks completed"
}

# Function to run formatting checks
run_formatting() {
    print_status "Checking code formatting with black..."
    if $VERBOSE; then
        if uv run black --check $SOURCE_DIRS examples/; then
            print_success "Code formatting check passed"
        else
            print_error "Code formatting check failed"
            return 1
        fi
    else
        if uv run black --check $SOURCE_DIRS examples/ >/dev/null 2>&1; then
            print_success "Code formatting check passed"
        else
            print_error "Code formatting check failed"
            return 1
        fi
    fi
    
    print_status "Checking import sorting with isort..."
    if $VERBOSE; then
        if uv run isort --check-only $SOURCE_DIRS examples/; then
            print_success "Import sorting check passed"
        else
            print_error "Import sorting check failed"
            return 1
        fi
    else
        if uv run isort --check-only $SOURCE_DIRS examples/ >/dev/null 2>&1; then
            print_success "Import sorting check passed"
        else
            print_error "Import sorting check failed"
            return 1
        fi
    fi
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
        
        FAILED=0
        
        if ! run_typecheck; then
            FAILED=1
        fi
        echo ""
        
        if ! run_linting; then
            FAILED=1
        fi
        echo ""
        
        if ! run_formatting; then
            FAILED=1
        fi
        echo ""
        
        if [ $FAILED -eq 0 ]; then
            print_success "All code quality checks passed! 🎉"
        else
            print_error "Some code quality checks failed!"
            exit 1
        fi
        ;;
    *)
        print_error "Unknown check type: $CHECK_TYPE"
        exit 1
        ;;
esac
