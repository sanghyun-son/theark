#!/bin/bash

# Help function - displayed at the top for easy access
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --host HOST        Bind socket to this host (default: 0.0.0.0)"
    echo "  --port PORT        Bind socket to this port (default: 8000)"
    echo "  --auto-reload      Enable auto-reload (default: enabled)"
    echo "  --no-reload        Disable auto-reload"
    echo "  --log-level LEVEL  Log level (default: info)"
    echo "  --prod             Production mode (no reload, warning log level)"
    echo "  --dev              Development mode (reload enabled, info log level)"
    echo "  --no-crawl         Disable historical crawling"
    echo "  --no-batch         Disable batch manager"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Start with default settings (auto-reload enabled)"
    echo "  $0 --auto-reload             # Start with auto-reload enabled (explicit)"
    echo "  $0 --port 3000              # Start on port 3000"
    echo "  $0 --prod                   # Start in production mode"
    echo "  $0 --dev                    # Start in development mode (with reload)"
    echo "  $0 --no-crawl               # Start without historical crawling"
    echo "  $0 --no-batch               # Start without batch manager"
    echo "  $0 --host 127.0.0.1 --port 8080 --auto-reload"
    exit 0
}

set -e

echo "🚀 Starting TheArk API Server..."

HOST="0.0.0.0"
PORT="9999"
RELOAD=""
LOG_LEVEL="info"
ENV="development"
NO_CRAWL=""
NO_BATCH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --auto-reload)
            RELOAD="--reload"
            shift
            ;;
        --no-reload)
            RELOAD=""
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --prod|--production)
            RELOAD=""
            LOG_LEVEL="warning"
            ENV="production"
            shift
            ;;
        --dev|--development)
            RELOAD="--reload"
            LOG_LEVEL="info"
            ENV="development"
            shift
            ;;
        --no-crawl)
            NO_CRAWL="--no-crawl"
            shift
            ;;
        --no-batch)
            NO_BATCH="--no-batch"
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"
export THEARK_ENV="$ENV"
export THEARK_LOG_LEVEL="$LOG_LEVEL"

# Disable historical crawling if --no-crawl is specified
if [ -n "$NO_CRAWL" ]; then
    export THEARK_HISTORICAL_CRAWL_ENABLED="false"
else
    export THEARK_HISTORICAL_CRAWL_ENABLED="true"
fi

# Disable batch manager if --no-batch is specified
if [ -n "$NO_BATCH" ]; then
    export THEARK_BATCH_MANAGER_ENABLED="false"
else
    export THEARK_BATCH_MANAGER_ENABLED="true"
fi

echo "📊 Server Configuration:"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Environment: $ENV"
echo "   Auto-reload: $([ -n "$RELOAD" ] && echo "enabled" || echo "disabled")"
echo "   Log Level: $LOG_LEVEL"
echo "   Historical Crawling: $([ -n "$NO_CRAWL" ] && echo "disabled" || echo "enabled")"
echo "   Batch Manager: $([ -n "$NO_BATCH" ] && echo "disabled" || echo "enabled")"
echo ""

echo "🔥 Launching uvicorn server..."
uv run uvicorn api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" \
    $RELOAD

echo "✅ Server stopped"
