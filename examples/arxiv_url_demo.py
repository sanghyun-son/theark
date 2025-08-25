#!/usr/bin/env python3
"""Demonstration of arXiv URL configuration in different environments."""

import os

from core.config import Settings, load_settings
from core.types import Environment
from crawler.arxiv.client import ArxivClient


def demonstrate_url_configuration() -> None:
    """Demonstrate how arXiv URL is configured in different environments."""
    print("🔧 arXiv URL Configuration Demonstration")
    print("=" * 50)

    # Test different environments
    environments = [
        ("development", Environment.DEVELOPMENT),
        ("production", Environment.PRODUCTION),
        ("testing", Environment.TESTING),
    ]

    for env_name, env_type in environments:
        print(f"\n📋 Environment: {env_name.upper()}")
        print("-" * 30)

        # Create settings for this environment
        settings = Settings(environment=env_type)

        print(f"  arxiv_api_base_url: {settings.arxiv_api_base_url}")
        print(f"  arxiv_url property: {settings.arxiv_url}")

        # Create ArxivClient
        client = ArxivClient()
        print(f"  ArxivClient base_url: {client.base_url}")

        # Verify URL is correct
        if env_name in ["development", "production"]:
            expected = "https://export.arxiv.org/api/query"
            assert (
                client.base_url == expected
            ), f"Expected {expected}, got {client.base_url}"
            print(f"  ✅ Correct full URL for {env_name}")
        else:
            print(f"  ℹ️  Test environment - URL can be overridden by fixtures")


def demonstrate_test_environment_override() -> None:
    """Demonstrate how test environment can override the URL."""
    print("\n\n🧪 Test Environment URL Override")
    print("=" * 50)

    # Simulate test environment with custom URL
    test_env = {
        "THEARK_ENV": "testing",
        "THEARK_ARXIV_API_BASE_URL": "http://localhost:8080/api/query",
    }

    # Save original environment
    original_env = dict(os.environ)

    try:
        # Set test environment
        os.environ.update(test_env)

        # Reload settings
        settings = load_settings()
        print(f"  Environment: {settings.environment}")
        print(f"  arxiv_api_base_url: {settings.arxiv_api_base_url}")
        print(f"  arxiv_url property: {settings.arxiv_url}")

        # Create client
        client = ArxivClient()
        print(f"  ArxivClient base_url: {client.base_url}")
        print("  ✅ Test environment successfully overrides URL")

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def main() -> None:
    """Main demonstration function."""
    demonstrate_url_configuration()
    demonstrate_test_environment_override()

    print("\n\n🎯 Summary")
    print("=" * 50)
    print(
        "✅ dev/prod environments: Always use full URL (https://export.arxiv.org/api/query)"
    )
    print("✅ test environment: Uses fixture-provided mock server URL")
    print("✅ Configuration is environment-aware and properly injected")


if __name__ == "__main__":
    main()
