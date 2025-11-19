"""
Main revelation module

It has the Revelation main class that creates the webserver do run
the presentation
"""

import json
import os
import re
import glob
import warnings
from pathlib import Path

from geventwebsocket import WebSocketApplication
from jinja2 import Environment, PackageLoader, select_autoescape
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from werkzeug.wrappers import Request, Response
# from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

from .config import Config
from .utils import normalize_newlines


class Revelation(object):
    """
    Main revelation app class that instantiates the server and handles
    the requests
    """

    def __init__(
        self,
        presentation,
        config=None,
        media=None,
        theme=None,
        style=None,
        reloader=False,
    ):
        """
        Initializes the server and creates the environment for the presentation

        Args:
            presentation: Path to presentation file or directory
            config: Path to configuration file
            media: Path to media directory
            theme: Path to theme directory
            style: Path to custom style CSS file
            reloader: Enable live reload functionality
        """
        self.config = Config(config)
        # Presentation can be either a file or directory
        self.presentation = self._validate_path(presentation, "presentation", must_exist=True, is_file=None)
        self.reloader = reloader

        shared_data = {
            "/static": os.path.join(os.path.dirname(__file__), "static")
        }

        # Validate and add media path
        if media:
            validated_media = self._validate_path(media, "media", must_exist=False)
            if validated_media:
                shared_data.update(self.parse_shared_data(validated_media))

        # Validate and add theme path
        if theme:
            validated_theme = self._validate_path(theme, "theme", must_exist=False)
            if validated_theme:
                shared_data.update(self.parse_shared_data(validated_theme))

        # Validate and add style path
        if style:
            validated_style = self._validate_path(style, "style", must_exist=True, is_file=True)
            if validated_style:
                self.style = os.path.basename(validated_style)
                shared_data.update(self.parse_shared_data(validated_style))
        else:
            self.style = None

        self.wsgi_app = SharedDataMiddleware(self.wsgi_app, shared_data)

    @staticmethod
    def _validate_path(path, path_type, must_exist=True, is_file=False):
        """
        Validate and sanitize file/directory paths to prevent path traversal attacks

        Args:
            path: The path to validate
            path_type: Description of path type (for error messages)
            must_exist: Whether the path must exist
            is_file: Whether the path should be a file (vs directory)

        Returns:
            str: Absolute validated path, or None if validation fails

        Raises:
            ValueError: If path contains suspicious patterns or fails validation
        """
        if not path:
            return None

        # Convert to Path object for safer operations
        try:
            path_obj = Path(path).resolve()
        except (ValueError, OSError) as e:
            warnings.warn(f"Invalid {path_type} path '{path}': {e}", UserWarning)
            return None

        # Security: Check for suspicious patterns
        path_str = str(path_obj)
        if '..' in Path(path).parts:
            raise ValueError(
                f"Path traversal detected in {path_type} path: {path}. "
                "Relative paths with '..' are not allowed for security reasons."
            )

        # Check existence if required
        if must_exist and not path_obj.exists():
            warnings.warn(
                f"{path_type.capitalize()} path does not exist: {path}",
                UserWarning
            )
            return None

        # Check if it's a file/directory as expected (only for specific types)
        if must_exist and is_file is not None:
            if is_file and not path_obj.is_file():
                warnings.warn(
                    f"{path_type.capitalize()} path is not a file: {path}",
                    UserWarning
                )
                return None
            elif not is_file and not path_obj.is_dir() and not path_obj.is_file():
                warnings.warn(
                    f"{path_type.capitalize()} path does not exist or is not accessible: {path}",
                    UserWarning
                )
                return None

        return str(path_obj)

    def parse_shared_data(self, shared_root):
        """
        Parse aditional shared_data if it exists
        """
        if shared_root:
            shared_root = os.path.abspath(shared_root)

            if os.path.exists(shared_root):
                shared_url = "/{}".format(os.path.basename(shared_root))

                return {shared_url: shared_root}

        return {}

    def load_slides(self, path, section_separator, vertical_separator):
        """
        Get slides file from the given path, loads it and split into list
        of slides.

        Args:
            path: Path to slide file or directory containing .md files
            section_separator: Regex pattern for horizontal slide separator
            vertical_separator: Regex pattern for vertical slide separator

        Returns:
            List of lists containing slide content

        Raises:
            FileNotFoundError: If no presentation files found
            IOError: If files cannot be read
            UnicodeDecodeError: If files contain invalid UTF-8
        """
        if os.path.isfile(path):
            lst_path = [path]
        else:
            lst_path = glob.glob(os.path.join(path, "*.md"))
            lst_path.sort()

        if not lst_path:
            raise FileNotFoundError(
                f"No presentation files found at {path}. "
                f"Expected either a .md file or a directory containing .md files."
            )

        slides = ""
        for slide_path in lst_path:
            try:
                with open(slide_path, "rb") as presentation:
                    content = presentation.read()
                    try:
                        decoded = content.decode("utf-8")
                    except UnicodeDecodeError as e:
                        raise UnicodeDecodeError(
                            e.encoding,
                            e.object,
                            e.start,
                            e.end,
                            f"Invalid UTF-8 in {slide_path}: {e.reason}"
                        )
                    slides += normalize_newlines(decoded)
            except IOError as e:
                raise IOError(f"Cannot read presentation file {slide_path}: {e}")

        try:
            return [
                re.split(
                    f"^{vertical_separator}$", section, flags=re.MULTILINE
                )
                for section in re.split(
                    f"^{section_separator}$", slides, flags=re.MULTILINE
                )
            ]
        except re.error as e:
            raise ValueError(
                f"Invalid separator regex pattern. "
                f"Section: '{section_separator}', Vertical: '{vertical_separator}'. "
                f"Error: {e}"
            )

    def get_theme(self, theme):
        reveal_theme = "static/revealjs/theme/{}.css".format(theme)
        fullpath_theme = os.path.join(os.path.dirname(__file__), reveal_theme)

        if os.path.isfile(fullpath_theme):
            return reveal_theme

        return theme

    def dispatch_request(self, request):
        """
        Handle HTTP requests and render the presentation

        Args:
            request: Werkzeug Request object

        Returns:
            Werkzeug Response object with rendered HTML

        Raises:
            Various exceptions for different error conditions
        """
        try:
            env = Environment(
                loader=PackageLoader("revelation", "templates"),
                autoescape=select_autoescape(["html"]),
            )

            # Load slides with proper error handling
            try:
                slides = self.load_slides(
                    self.presentation,
                    self.config.get("REVEAL_SLIDE_SEPARATOR"),
                    self.config.get("REVEAL_VERTICAL_SLIDE_SEPARATOR"),
                )
            except (FileNotFoundError, IOError, UnicodeDecodeError, ValueError) as e:
                error_msg = f"Error loading presentation slides: {e}"
                return Response(
                    f"<html><body><h1>Error Loading Presentation</h1><pre>{error_msg}</pre></body></html>",
                    status=500,
                    headers={"content-type": "text/html"}
                )

            context = {
                "meta": self.config.get("REVEAL_META"),
                "slides": slides,
                "config": self.config.get("REVEAL_CONFIG"),
                "theme": self.get_theme(self.config.get("REVEAL_THEME")),
                "style": self.style,
                "reloader": self.reloader,
                "static_revealjs": "static/revealjs",
                "logo": self.config.get("REVEAL_THEME_LOGO"),
                "licence": self.config.get("REVEAL_LICENCE"),
            }

            template_file = self.config.get("REVEAL_TEMPLATE")
            if template_file is None:
                template_file = "presentation.html"

            try:
                template = env.get_template(template_file)
            except Exception as e:
                error_msg = f"Template '{template_file}' not found: {e}"
                warnings.warn(error_msg, UserWarning)
                # Fallback to default template
                template = env.get_template("presentation.html")

            try:
                rendered = template.render(**context)
            except Exception as e:
                error_msg = f"Error rendering template: {e}"
                return Response(
                    f"<html><body><h1>Template Rendering Error</h1><pre>{error_msg}</pre></body></html>",
                    status=500,
                    headers={"content-type": "text/html"}
                )

            return Response(rendered, headers={"content-type": "text/html"})

        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error: {e}"
            warnings.warn(error_msg, RuntimeWarning)
            import traceback
            traceback.print_exc()
            return Response(
                f"<html><body><h1>Internal Server Error</h1><pre>{error_msg}</pre></body></html>",
                status=500,
                headers={"content-type": "text/html"}
            )

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)

        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


class PresentationReloadWebSocketSendEvent(FileSystemEventHandler):
    """
    Handler class to notify throughout the websocket
    when a tracked file changes
    """

    def __init__(self, ws):
        self.ws = ws

    def on_modified(self, event):
        """Handle file modification events"""
        try:
            if event.src_path.endswith((".md", ".css")) and not self.ws.closed:
                self.ws.send(
                    json.dumps({"msg_type": "message", "message": "reload"})
                )
        except Exception as e:
            # Log error but don't crash the watcher
            warnings.warn(f"Error sending reload notification: {e}", RuntimeWarning)


class PresentationReloader(WebSocketApplication):
    """WebSocket to notify the frontend on file changes with proper resource cleanup"""

    tracking_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observer = None
        self.event_handler = None

    def on_open(self):
        """Initialize file system observer when WebSocket opens"""
        if self.tracking_path:
            try:
                self.event_handler = PresentationReloadWebSocketSendEvent(self.ws)
                self.observer = Observer()
                self.observer.schedule(self.event_handler, self.tracking_path, recursive=True)
                self.observer.start()
            except Exception as e:
                warnings.warn(
                    f"Failed to start file system observer: {e}",
                    RuntimeWarning
                )
                # Clean up if initialization failed
                if self.observer:
                    try:
                        self.observer.stop()
                    except:
                        pass
                self.observer = None
                self.event_handler = None

    def on_message(self, message, *args, **kwargs):
        """Handle incoming WebSocket messages (currently unused)"""
        pass

    def on_close(self, reason):
        """Clean up resources when WebSocket closes"""
        if self.observer:
            try:
                self.observer.stop()
                # IMPORTANT: Join to ensure thread cleanup
                self.observer.join(timeout=2.0)
            except Exception as e:
                warnings.warn(
                    f"Error stopping file system observer: {e}",
                    RuntimeWarning
                )
            finally:
                self.observer = None
                self.event_handler = None
