"""Revelation configuration handler"""

import os
import types
import warnings

from werkzeug.utils import import_string

from . import default_config

try:
    import tomllib
except ModuleNotFoundError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class Config(dict):
    """
    Class that stores revelation configs thanks to flask Config:

    https://github.com/pallets/flask/blob/master/flask/config.py

    It loads the default_config variables and if a path is passed it also
    loads the external configs.

    Supports both TOML (preferred, secure) and Python (legacy, deprecated) config files.
    """

    # Allowed configuration keys for security
    ALLOWED_CONFIG_KEYS = {
        "REVEAL_META",
        "REVEAL_SLIDE_SEPARATOR",
        "REVEAL_VERTICAL_SLIDE_SEPARATOR",
        "REVEAL_THEME",
        "REVEAL_THEME_LOGO",
        "REVEAL_LICENCE",
        "REVEAL_TEMPLATE",
        "REVEAL_CONFIG",
    }

    def __init__(self, filename=None):
        """Initializes the config with the defaults or with custom
        variables from an external file"""
        self.load_from_object(default_config)

        if filename and os.path.isfile(filename):
            if filename.endswith('.toml'):
                self.load_from_toml(filename)
            elif filename.endswith('.py'):
                warnings.warn(
                    "Python config files are deprecated and will be removed in a future version. "
                    "Please migrate to TOML format (.toml). "
                    "Python config files pose security risks due to arbitrary code execution.",
                    DeprecationWarning,
                    stacklevel=2
                )
                self.load_from_pyfile(filename)
            else:
                # Try to auto-detect format
                try:
                    self.load_from_toml(filename)
                except Exception:
                    self.load_from_pyfile(filename)

    def load_from_object(self, obj):
        """Load the configs from a python object passed
        to the function"""
        if isinstance(obj, str):
            obj = import_string(obj)

        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def load_from_toml(self, filename):
        """Load the configs from a TOML file (secure method)

        Args:
            filename: Path to TOML configuration file

        Raises:
            ImportError: If tomllib/tomli is not available
            IOError: If file cannot be read
            ValueError: If config contains disallowed keys
        """
        if tomllib is None:
            raise ImportError(
                "TOML support requires 'tomli' package for Python < 3.11. "
                "Install with: pip install tomli"
            )

        try:
            with open(filename, "rb") as config_file:
                config_data = tomllib.load(config_file)
        except IOError as error:
            error.strerror = f"Unable to load configuration file ({error.strerror})"
            raise
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"Invalid TOML syntax in {filename}: {error}")

        # Validate and load configuration
        for key, value in config_data.items():
            upper_key = key.upper()

            # Security: Only allow known configuration keys
            if upper_key not in self.ALLOWED_CONFIG_KEYS:
                warnings.warn(
                    f"Unknown configuration key '{key}' will be ignored. "
                    f"Allowed keys: {', '.join(sorted(self.ALLOWED_CONFIG_KEYS))}",
                    UserWarning,
                    stacklevel=2
                )
                continue

            # Validate types for known configs
            if not self._validate_config_value(upper_key, value):
                warnings.warn(
                    f"Invalid type for configuration key '{key}', skipping",
                    UserWarning,
                    stacklevel=2
                )
                continue

            self[upper_key] = value

        # Handle config keys nested in reveal_meta (common user mistake in TOML)
        # Extract them to root level where they belong
        reveal_meta = self.get("REVEAL_META", {})
        if isinstance(reveal_meta, dict):
            keys_to_extract = [
                "reveal_licence",
                "reveal_slide_separator",
                "reveal_vertical_slide_separator",
                "reveal_theme",
                "reveal_theme_logo",
                "reveal_template",
            ]
            for key in keys_to_extract:
                upper_key = key.upper()
                if key in reveal_meta:
                    self[upper_key] = reveal_meta.pop(key)

    def _validate_config_value(self, key, value):
        """Validate configuration value types

        Args:
            key: Configuration key (uppercase)
            value: Configuration value

        Returns:
            bool: True if valid, False otherwise
        """
        if key == "REVEAL_META":
            return isinstance(value, dict)
        elif key in ("REVEAL_SLIDE_SEPARATOR", "REVEAL_VERTICAL_SLIDE_SEPARATOR",
                     "REVEAL_THEME", "REVEAL_THEME_LOGO", "REVEAL_LICENCE", "REVEAL_TEMPLATE"):
            return isinstance(value, str)
        elif key == "REVEAL_CONFIG":
            return isinstance(value, dict)
        return True

    def load_from_pyfile(self, filename):
        """Load the configs from a python file (DEPRECATED - SECURITY RISK)

        WARNING: This method uses exec() and can execute arbitrary code.
        Use TOML format instead for secure configuration.

        Args:
            filename: Path to Python configuration file
        """
        module = types.ModuleType("config")
        module.__file__ = filename

        # Restricted globals to limit damage from malicious configs
        restricted_globals = {
            "__builtins__": {
                "True": True,
                "False": False,
                "None": None,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
            }
        }

        try:
            with open(filename, mode="rb") as config_file:
                code = compile(config_file.read(), filename, "exec")
                # Execute with restricted globals
                exec(code, restricted_globals, module.__dict__)
        except IOError as error:
            error.strerror = f"Unable to load configuration file ({error.strerror})"
            raise
        except Exception as error:
            raise ValueError(f"Error executing config file {filename}: {error}")

        self.load_from_object(module)
