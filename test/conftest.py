"""Pytest configuration for Instagiffer test suite."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--app-package",
        default=None,
        help="Path to a frozen .app bundle (e.g. /Applications/Instagiffer.app). When set, tests run against the installed app instead of the dev source.",
    )


@pytest.fixture
def app_package(request):
    return request.config.getoption("--app-package")
