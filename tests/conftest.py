"""Pytest configuration for Django integration."""

import pytest


def pytest_collection_modifyitems(items):
    """Automatically add django_db marker to all tests."""
    for item in items:
        item.add_marker(pytest.mark.django_db)
