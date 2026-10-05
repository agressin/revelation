import shutil
import tempfile
from pathlib import Path

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from revelation import Revelation


@pytest.fixture
def tests_folder(tmp_path):
    """Provide a temporary test directory"""
    return tmp_path


@pytest.fixture
def media_folder(tests_folder):
    """Provide a media folder in the test directory"""
    media = tests_folder / "media"
    media.mkdir()
    return media


@pytest.fixture
def slide_file(tests_folder):
    """Provide a basic slide file"""
    slide = tests_folder / "slides.md"
    slide.write_text("# Pag1\n---\n# Pag2.1\n---~\n# Page2.2")
    return slide


@pytest.fixture
def non_normalized_slide(tests_folder):
    """Provide a slide file with non-normalized line endings"""
    slide = tests_folder / "non_normalized.md"
    slide.write_text("# Pag1\r---\r\n# Pag2")
    return slide


@pytest.fixture
def non_ascii_slide(tests_folder):
    """Provide a slide file with non-ASCII characters"""
    slide = tests_folder / "non_ascii.md"
    slide.write_text("# こんにちは\n---\n# 乾杯")
    return slide


@pytest.fixture
def revelation_app(slide_file, media_folder):
    """Provide a configured Revelation app instance"""
    return Revelation(str(slide_file), media=str(media_folder))

def test_parse_shared_data_empty(revelation_app):
    """Test that parsing None returns empty dict"""
    shared_data_config = revelation_app.parse_shared_data(None)
    assert shared_data_config == {}


def test_parse_shared_data(revelation_app, media_folder):
    """Test that parsing media folder returns correct mapping"""
    shared_data_config = revelation_app.parse_shared_data(str(media_folder))
    expected = {f"/{media_folder.name}": str(media_folder)}
    assert shared_data_config == expected


def test_load_slides(revelation_app, slide_file):
    """Test loading and parsing slides with separators"""
    slides = revelation_app.load_slides(str(slide_file), "---", "---~")
    assert slides == [["# Pag1\n"], ["\n# Pag2.1\n", "\n# Page2.2"]]


def test_load_slides_non_normalized(revelation_app, non_normalized_slide):
    """Test that line endings are normalized"""
    slides = revelation_app.load_slides(str(non_normalized_slide), "---", "---~")
    assert slides == [["# Pag1\n"], ["\n# Pag2"]]


def test_load_slides_non_ascii(revelation_app, non_ascii_slide):
    """Test handling of non-ASCII characters"""
    slides = revelation_app.load_slides(str(non_ascii_slide), "---", "---~")
    assert slides == [["# こんにちは\n"], ["\n# 乾杯"]]


def test_client_request_ok(revelation_app):
    """Test that HTTP request returns 200 OK"""
    client = Client(revelation_app, Response)
    response = client.get("/")
    assert response.status == "200 OK"
    assert response.headers.get("Content-Type") == "text/html"


def test_client_with_reload(tests_folder, media_folder):
    """Test that reloader script is included when enabled"""
    # Create slide and config with myPresentation.html template
    slide = tests_folder / "slides.md"
    slide.write_text("# Test")

    config_file = tests_folder / "config.py"
    config_file.write_text('REVEAL_TEMPLATE = "myPresentation.html"')

    app = Revelation(str(slide), config=str(config_file), media=str(media_folder), reloader=True)
    client = Client(app, Response)
    response = client.get("/")
    assert "reloader" in response.data.decode("utf8")


def test_client_without_reload(slide_file, media_folder):
    """Test that reloader script is excluded when disabled"""
    app = Revelation(str(slide_file), media=str(media_folder), reloader=False)
    client = Client(app, Response)
    response = client.get("/")
    assert "reloader" not in response.data.decode("utf8")


def test_default_template_is_mypresentation(tests_folder):
    """Without REVEAL_TEMPLATE, the reveal.js 5.x template is used"""
    slide = tests_folder / "slides.md"
    slide.write_text("# Test")
    config_file = tests_folder / "config.toml"
    config_file.write_text('[reveal_meta]\ntitle = "T"\n')

    app = Revelation(str(slide), config=str(config_file))
    app.config.pop("REVEAL_TEMPLATE", None)
    response = Client(app, Response).get("/")
    assert response.status_code == 200
    assert "RevealTimeTimer" in response.data.decode("utf8")


def test_missing_template_returns_explicit_error(tests_folder):
    """An unknown REVEAL_TEMPLATE gives a readable 500, not a silent fallback"""
    slide = tests_folder / "slides.md"
    slide.write_text("# Test")
    config_file = tests_folder / "config.toml"
    config_file.write_text('reveal_template = "nope.html"\n')

    app = Revelation(str(slide), config=str(config_file))
    with pytest.warns(UserWarning, match="nope.html"):
        response = Client(app, Response).get("/")
    body = response.data.decode("utf8")
    assert response.status_code == 500
    assert "nope.html" in body
    assert "myPresentation.html" in body
