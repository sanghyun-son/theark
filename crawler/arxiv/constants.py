"""Constants for arXiv crawler module."""

from typing import Final

# arXiv API constants
ARXIV_API_BASE_URL: Final[str] = "https://export.arxiv.org/api/query"
ARXIV_ABS_BASE_URL: Final[str] = "https://arxiv.org/abs"
ARXIV_PDF_BASE_URL: Final[str] = "https://arxiv.org/pdf"

# XML namespaces
ARXIV_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# Default values
DEFAULT_PRIMARY_CATEGORY = "cs.AI"
DEFAULT_RATE_LIMIT = 0.33  # requests per second
DEFAULT_BACKGROUND_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_MAX_CONCURRENT_PAPERS = 3
DEFAULT_MAX_PAPERS_PER_BATCH = 100
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 60  # seconds
DEFAULT_BATCH_SIZE = 10
DEFAULT_RECENT_PAPERS_LIMIT = 50
DEFAULT_MONTHLY_PAPERS_LIMIT = 200

# HTTP constants
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = "theark-arxiv-crawler/1.0 (https://github.com/your-repo/theark)"

# Date format
ISO8601_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Error messages
ERROR_NO_PAPERS_FOUND = "No papers found in XML response"
ERROR_FAILED_TO_PARSE_XML = "Failed to parse XML: {}"
ERROR_EXTRACTING_ARXIV_ID = "Could not extract arXiv ID from entry"
ERROR_INVALID_DATE_FORMAT = "Could not parse date: {}"

# Log messages
LOG_SUCCESSFULLY_PARSED = "Successfully parsed paper: {} - {}"
LOG_FOUND_PRIMARY_CATEGORY = "Found primary category: {}"
LOG_FOUND_CATEGORY = "Found category: {}"
LOG_FOUND_ARXIV_CATEGORY = "Found arxiv:category: {}"
LOG_FINAL_CATEGORIES = "Final categories: {}"
