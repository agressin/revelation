"""Shared test fixtures"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def no_web_browser():
    """Never open a real web browser from the tests (revelation start)"""
    with patch("webbrowser.open") as mock_open:
        yield mock_open


@pytest.fixture(autouse=True)
def fake_revealjs(tmp_path_factory, monkeypatch):
    """Minimal reveal.js folder: tests never need (nor download) reveal.js"""
    folder = tmp_path_factory.mktemp("revealjs")
    (folder / "reveal.js").write_text("// fake reveal.js for tests\n")
    (folder / "reveal.css").write_text("/* fake */\n")
    monkeypatch.setattr("revelation.cli.REVEALJS_FOLDER", str(folder))
    return folder
