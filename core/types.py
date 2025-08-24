"""Common type definitions for the theark system."""

from enum import Enum


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
