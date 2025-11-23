"""Pytest configuration for Django integration."""

import os
import pytest


def pytest_collection_modifyitems(items):
    """Automatically add django_db marker to all tests and skip local_only in CI."""
    # Detect CI environment
    is_ci = any([
        os.getenv('CI'),  # GitHub Actions, GitLab CI
        os.getenv('GITHUB_ACTIONS'),
        os.getenv('CONTINUOUS_INTEGRATION'),
    ])

    skip_local_only = pytest.mark.skip(reason="Skipped: local_only tests don't run in CI/CD")

    for item in items:
        # Check if it is an async test (marked with @pytest.mark.asyncio)
        is_async = item.get_closest_marker("asyncio") is not None

        # Add django_db marker
        # Use transaction=True for async tests to avoid SQLite locking issues with threads
        if is_async:
            item.add_marker(pytest.mark.django_db(transaction=True))
        else:
            item.add_marker(pytest.mark.django_db)

        # Skip tests marked with local_only in CI environments
        if is_ci and 'local_only' in item.keywords:
            item.add_marker(skip_local_only)
