"""API-related constants and literals."""

from enum import Enum, IntEnum

# HTTP Headers
STREAMING_HEADERS = {"Accept": "text/event-stream"}
JSON_HEADERS = {"Content-Type": "application/json"}
HTML_HEADERS = {"Content-Type": "text/html"}

# Content Types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_EVENT_STREAM = "text/event-stream"

# API Endpoints
API_V1_PREFIX = "/v1"
PAPERS_BASE_PATH = f"{API_V1_PREFIX}/papers"
CONFIG_BASE_PATH = f"{API_V1_PREFIX}/config"
HEALTH_ENDPOINT = "/health"
DOCS_ENDPOINT = "/docs"
OPENAPI_ENDPOINT = "/openapi.json"

# Papers endpoints
PAPERS_STREAM_SUMMARY_PATH = f"{PAPERS_BASE_PATH}/stream-summary"
PAPERS_CRUD_PATH = PAPERS_BASE_PATH
PAPERS_STAR_PATH = f"{PAPERS_BASE_PATH}/starred"

# Config endpoints
CONFIG_CATEGORIES_PATH = f"{CONFIG_BASE_PATH}/categories"

# Paper-related constants
DEFAULT_SUMMARY_LANGUAGE = "English"
SUPPORTED_LANGUAGES = ["English", "Korean"]

# Query parameter defaults
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0
DEFAULT_LANGUAGE = "Korean"

# Pagination limits
MIN_LIMIT = 1
MAX_LIMIT = 100
MIN_OFFSET = 0

# Authentication
AUTH_HEADER = "Authorization"
AUTH_PREFIX = "Bearer"

# Public endpoints (no auth required)
PUBLIC_ENDPOINTS = [
    HEALTH_ENDPOINT,
    DOCS_ENDPOINT,
    OPENAPI_ENDPOINT,
    "/",
    "/favicon.ico",
]


class EventType(str, Enum):
    """Event types for streaming responses."""

    STATUS = "status"
    COMPLETE = "complete"
    ERROR = "error"


class HTTPStatus(IntEnum):
    """HTTP status codes."""

    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


class ContentType(str, Enum):
    """Content types for HTTP responses."""

    JSON = "application/json"
    HTML = "text/html"
    EVENT_STREAM = "text/event-stream"
    PLAIN_TEXT = "text/plain"
