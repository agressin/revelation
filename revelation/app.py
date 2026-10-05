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
from typing import Any, Dict, List, Optional, Union

from geventwebsocket import WebSocketApplication
from jinja2 import Environment, PackageLoader, TemplateNotFound, select_autoescape
from markupsafe import escape
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from werkzeug.wrappers import Request, Response
# from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

from .config import Config
from .utils import normalize_newlines

# Template used when REVEAL_TEMPLATE is not set (reveal.js 5.x layout)
DEFAULT_TEMPLATE = "myPresentation.html"


class Revelation:
    """
    Main revelation app class that instantiates the server and handles
    the requests
    """

    def __init__(
        self,
        presentation: str,
        config: Optional[str] = None,
        media: Optional[str] = None,
        theme: Optional[str] = None,
        style: Optional[str] = None,
        reloader: bool = False,
    ) -> None:
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
                self.style: Optional[str] = os.path.basename(validated_style)
                shared_data.update(self.parse_shared_data(validated_style))
            else:
                self.style = None
        else:
            self.style = None

        # Create WSGI middleware wrapper
        wsgi_app_func = self.wsgi_app
        self.wsgi_app = SharedDataMiddleware(wsgi_app_func, shared_data)  # type: ignore[method-assign]

    @staticmethod
    def _validate_path(
        path: Optional[str],
        path_type: str,
        must_exist: bool = True,
        is_file: Optional[bool] = False,
    ) -> Optional[str]:
        """
        Validate and sanitize file/directory paths to prevent path traversal attacks

        Args:
            path: The path to validate
            path_type: Description of path type (for error messages)
            must_exist: Whether the path must exist
            is_file: Whether the path should be a file (vs directory), None for either

        Returns:
            Absolute validated path, or None if validation fails

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

    def parse_shared_data(self, shared_root: Optional[str]) -> Dict[str, str]:
        """
        Parse additional shared_data if it exists

        Args:
            shared_root: Path to shared data directory

        Returns:
            Dictionary mapping URL paths to filesystem paths
        """
        if shared_root:
            shared_root = os.path.abspath(shared_root)

            if os.path.exists(shared_root):
                shared_url = "/{}".format(os.path.basename(shared_root))

                return {shared_url: shared_root}

        return {}

    def load_slides(
        self,
        path: str,
        section_separator: str,
        vertical_separator: str
    ) -> List[List[str]]:
        """
        Get slides file from the given path, loads it and split into list
        of slides.

        Args:
            path: Path to slide file or directory containing .md files
            section_separator: Regex pattern for horizontal slide separator
            vertical_separator: Regex pattern for vertical slide separator

        Returns:
            List of lists containing slide content (nested structure for vertical slides)

        Raises:
            FileNotFoundError: If no presentation files found
            IOError: If files cannot be read
            UnicodeDecodeError: If files contain invalid UTF-8
            ValueError: If separator regex patterns are invalid
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

    def get_theme(self, theme: str) -> str:
        """
        Get theme CSS path, checking if it's a built-in theme

        Args:
            theme: Theme name or custom path

        Returns:
            Theme CSS path (relative or custom)
        """
        reveal_theme = f"static/revealjs/theme/{theme}.css"
        fullpath_theme = os.path.join(os.path.dirname(__file__), reveal_theme)

        if os.path.isfile(fullpath_theme):
            return reveal_theme

        return theme

    def dispatch_request(self, request: Request) -> Response:
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
                presentation_path = self.presentation if self.presentation else ""
                section_sep = str(self.config.get("REVEAL_SLIDE_SEPARATOR", "---"))
                vertical_sep = str(self.config.get("REVEAL_VERTICAL_SLIDE_SEPARATOR", "--"))

                slides = self.load_slides(presentation_path, section_sep, vertical_sep)
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
                "theme": self.get_theme(str(self.config.get("REVEAL_THEME", "black"))),
                "style": self.style,
                "reloader": self.reloader,
                "static_revealjs": "static/revealjs",
                "logo": self.config.get("REVEAL_THEME_LOGO"),
                "licence": self.config.get("REVEAL_LICENCE"),
            }

            template_file = self.config.get("REVEAL_TEMPLATE") or DEFAULT_TEMPLATE

            try:
                template = env.get_template(template_file)
            except TemplateNotFound:
                # No silent fallback: another template would render a blank
                # page (different reveal.js layout), which is harder to debug.
                available = ", ".join(sorted(env.list_templates(extensions=["html"])))
                error_msg = (
                    f"Template '{template_file}' (REVEAL_TEMPLATE) not found.\n"
                    f"Available templates: {available}\n"
                    f"Fix REVEAL_TEMPLATE in your config, or remove it to use "
                    f"the default ({DEFAULT_TEMPLATE})."
                )
                warnings.warn(error_msg, UserWarning)
                return Response(
                    f"<html><body><h1>Template Not Found</h1><pre>{escape(error_msg)}</pre></body></html>",
                    status=500,
                    headers={"content-type": "text/html"}
                )

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

    def wsgi_app(self, environ: Dict[str, Any], start_response: Any) -> Any:
        """
        WSGI application interface

        Args:
            environ: WSGI environment dict
            start_response: WSGI start_response callable

        Returns:
            WSGI response
        """
        request = Request(environ)
        response = self.dispatch_request(request)

        return response(environ, start_response)

    def __call__(self, environ: Dict[str, Any], start_response: Any) -> Any:
        """Make the app callable as WSGI application"""
        return self.wsgi_app(environ, start_response)


class PresentationReloadWebSocketSendEvent(FileSystemEventHandler):
    """
    Handler class to notify throughout the websocket
    when a tracked file changes
    """

    def __init__(self, ws: Any) -> None:
        """
        Initialize event handler with WebSocket

        Args:
            ws: WebSocket connection object
        """
        self.ws = ws

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events

        Args:
            event: File system event object
        """
        try:
            src_path = str(event.src_path)
            if src_path.endswith((".md", ".css")) and not self.ws.closed:
                self.ws.send(
                    json.dumps({"msg_type": "message", "message": "reload"})
                )
        except Exception as e:
            # Log error but don't crash the watcher
            warnings.warn(f"Error sending reload notification: {e}", RuntimeWarning)


class PresentationReloader(WebSocketApplication):
    """WebSocket to notify the frontend on file changes with proper resource cleanup"""

    tracking_path: Optional[str] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize WebSocket reloader

        Args:
            *args: Positional arguments for WebSocketApplication
            **kwargs: Keyword arguments for WebSocketApplication
        """
        super().__init__(*args, **kwargs)
        self.observer: Optional[Any] = None  # Observer type is complex
        self.event_handler: Optional[PresentationReloadWebSocketSendEvent] = None

    def on_open(self) -> None:
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

    def on_message(self, message: Any, *args: Any, **kwargs: Any) -> None:
        """
        Handle incoming WebSocket messages (currently unused)

        Args:
            message: Incoming message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        pass

    def on_close(self, reason: Any) -> None:
        """
        Clean up resources when WebSocket closes

        Args:
            reason: Close reason
        """
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
