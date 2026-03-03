"""Pytest configuration for Instagiffer test suite."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--app",
        default=None,
        help="Path to the frozen app to test against. macOS: path to .app bundle. Windows: path to .exe.",
    )


@pytest.fixture
def app_path(request):
    return request.config.getoption("--app")
