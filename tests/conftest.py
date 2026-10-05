"""Shared test fixtures"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_web_browser():
    """Never open a real web browser from the tests (revelation start)"""
    with patch("webbrowser.open") as mock_open:
        yield mock_open
