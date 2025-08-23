"""Application constants and configuration values."""

from typing import Final

# OpenAI pricing per 1M tokens (as of 2024)
# Source: https://platform.openai.com/docs/pricing?latest-pricing=standard
OPENAI_PRICING: Final[dict[str, dict[str, float]]] = {
    # GPT-5 models
    "gpt-5": {"input": 1.25, "output": 10.00},
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-5-chat-latest": {"input": 1.25, "output": 10.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
    "gpt-4o-audio-preview": {"input": 2.50, "output": 10.00},
    "gpt-4o-realtime-preview": {"input": 5.00, "output": 20.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-audio-preview": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-realtime-preview": {"input": 0.60, "output": 2.40},
    "gpt-4o-search-preview": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini-search-preview": {"input": 0.15, "output": 0.60},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-pro": {"input": 150.00, "output": 600.00},
    "o1-mini": {"input": 1.10, "output": 4.40},
    "o3": {"input": 2.00, "output": 8.00},
    "o3-pro": {"input": 20.00, "output": 80.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "o3-deep-research": {"input": 10.00, "output": 40.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "o4-mini-deep-research": {"input": 2.00, "output": 8.00},
    "codex-mini-latest": {"input": 1.50, "output": 6.00},
    "computer-use-preview": {"input": 3.00, "output": 12.00},
    "gpt-image-1": {"input": 5.00, "output": 0.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "default": {"input": 1.00, "output": 2.00},
}

# Batch processing discount (50% off for batch processing)
BATCH_DISCOUNT_MULTIPLIER: Final[float] = 0.5

# Cost calculation precision (decimal places)
COST_PRECISION: Final[int] = 6

# Token conversion factor (per 1M tokens)
TOKENS_PER_MILLION: Final[int] = 1_000_000
