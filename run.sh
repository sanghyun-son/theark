#!/bin/bash

# TheArk API Server Launcher
set -e

echo "🚀 Starting TheArk API Server..."

# Default values
HOST="0.0.0.0"
PORT="8000"
RELOAD="--reload"
LOG_LEVEL="info"

# Parse command line arguments
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
        --no-reload)
            RELOAD=""
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --prod)
            RELOAD=""
            LOG_LEVEL="warning"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST        Bind socket to this host (default: 0.0.0.0)"
            echo "  --port PORT        Bind socket to this port (default: 8000)"
            echo "  --no-reload        Disable auto-reload"
            echo "  --log-level LEVEL  Log level (default: info)"
            echo "  --prod             Production mode (no reload, warning log level)"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Start with default settings"
            echo "  $0 --port 3000              # Start on port 3000"
            echo "  $0 --prod                   # Start in production mode"
            echo "  $0 --host 127.0.0.1 --port 8080 --no-reload"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"

echo "📊 Server Configuration:"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Reload: $([ -n "$RELOAD" ] && echo "enabled" || echo "disabled")"
echo "   Log Level: $LOG_LEVEL"
echo ""

# Start the server
echo "🔥 Launching uvicorn server..."
uv run uvicorn api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" \
    $RELOAD

echo "✅ Server stopped"
