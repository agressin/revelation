"""Rendering checks for myPresentation.html (template used by the courses)"""

from html.parser import HTMLParser

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from revelation import Revelation


class ResourceCollector(HTMLParser):
    """Collect URLs loaded as scripts or stylesheets, and all links"""

    def __init__(self):
        super().__init__()
        self.loaded = []   # (tag, url) fetched by the browser on page load
        self.anchors = []  # clickable links (<a href>)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.loaded.append((tag, attrs["src"]))
        elif tag == "link" and "stylesheet" in (attrs.get("rel") or "").split():
            self.loaded.append((tag, attrs.get("href", "")))
        elif tag == "img" and attrs.get("src"):
            self.loaded.append((tag, attrs["src"]))
        elif tag == "a" and attrs.get("href"):
            self.anchors.append(attrs["href"])


@pytest.fixture
def rendered(tmp_path):
    def render(reloader=False):
        slide = tmp_path / "slides.md"
        slide.write_text("# Test\n---\n# Two")
        config = tmp_path / "config.toml"
        config.write_text(
            'reveal_template = "myPresentation.html"\n'
            'reveal_licence = "by-sa"\n'
            'reveal_theme = "heig_ec+g"\n'
            'reveal_theme_logo = "gte"\n'
        )
        app = Revelation(str(slide), config=str(config), reloader=reloader)
        response = Client(app, Response).get("/")
        assert response.status_code == 200
        return response.data.decode("utf8")
    return render


def test_no_remote_script_or_stylesheet(rendered):
    """Everything is served locally: no network needed in class or for PDF"""
    parser = ResourceCollector()
    parser.feed(rendered())
    assert parser.loaded, "no script/stylesheet found, parser broken?"
    remote = [
        (tag, url) for tag, url in parser.loaded
        if url.lower().startswith(("http://", "https://", "//"))
    ]
    assert remote == []
    # The only remote URL allowed is the clickable CC licence link
    for href in parser.anchors:
        if href.startswith(("http://", "https://")):
            assert "creativecommons.org/licenses/" in href


def test_reloader_uses_current_host(rendered):
    html = rendered(reloader=True)
    assert "location.host + '/reloader'" in html
    assert "localhost:4000" not in html


def test_no_reloader_when_disabled(rendered):
    assert "/reloader" not in rendered(reloader=False)
