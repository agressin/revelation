"""Tests for TOML configuration support"""

import shutil
import tempfile
import warnings
from pathlib import Path
from unittest import TestCase

from revelation.config import Config


class ConfigTomlTestCase(TestCase):
    def setUp(self):
        self.tests_folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_config_load_toml(self):
        """Test loading a valid TOML configuration"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
[reveal_meta]
title = "Test Title"
author = "Test Author"
description = "Test description"

reveal_theme = "black"
reveal_slide_separator = "---"
""")

        config = Config(str(config_file))

        self.assertIsInstance(config, dict)
        self.assertIn("REVEAL_META", config)
        self.assertEqual(config["REVEAL_META"]["title"], "Test Title")
        self.assertEqual(config["REVEAL_META"]["author"], "Test Author")
        self.assertEqual(config["REVEAL_THEME"], "black")

    def test_config_load_toml_with_config_dict(self):
        """Test loading TOML with reveal_config section"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
reveal_theme = "moon"

[reveal_config]
controls = true
progress = false
slideNumber = "c/t"
""")

        config = Config(str(config_file))

        self.assertEqual(config["REVEAL_THEME"], "moon")
        self.assertIsInstance(config["REVEAL_CONFIG"], dict)
        self.assertTrue(config["REVEAL_CONFIG"]["controls"])
        self.assertFalse(config["REVEAL_CONFIG"]["progress"])
        self.assertEqual(config["REVEAL_CONFIG"]["slideNumber"], "c/t")

    def test_config_toml_unknown_key_warning(self):
        """Test that unknown keys in TOML generate warnings"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
reveal_theme = "night"
unknown_key = "should be ignored"
another_bad_key = 123
""")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = Config(str(config_file))

            # Should have warnings for unknown keys
            warning_messages = [str(warning.message) for warning in w]
            self.assertTrue(
                any("unknown_key" in msg.lower() for msg in warning_messages)
            )

        # Unknown keys should not be in config
        self.assertNotIn("UNKNOWN_KEY", config)
        self.assertNotIn("ANOTHER_BAD_KEY", config)
        # Valid key should be present
        self.assertEqual(config["REVEAL_THEME"], "night")

    def test_config_toml_invalid_type(self):
        """Test that invalid types generate warnings"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
reveal_theme = 123  # Should be string
reveal_slide_separator = "---"
""")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = Config(str(config_file))

            # Should have warning about invalid type
            warning_messages = [str(warning.message) for warning in w]
            self.assertTrue(
                any("invalid type" in msg.lower() for msg in warning_messages)
            )

        # Invalid value should not override default
        self.assertNotEqual(config["REVEAL_THEME"], 123)

    def test_config_toml_invalid_syntax(self):
        """Test handling of invalid TOML syntax"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
this is not valid TOML
[unclosed section
""")

        with self.assertRaises(ValueError) as context:
            Config(str(config_file))

        self.assertIn("Invalid TOML syntax", str(context.exception))

    def test_config_python_deprecation_warning(self):
        """Test that Python config files generate deprecation warnings"""
        config_file = Path(self.tests_folder) / "config.py"
        config_file.write_text("""
REVEAL_THEME = "sky"
""")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = Config(str(config_file))

            # Should have deprecation warning
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            self.assertTrue(len(deprecation_warnings) > 0)

            warning_msg = str(deprecation_warnings[0].message)
            self.assertIn("deprecated", warning_msg.lower())
            self.assertIn("TOML", warning_msg)

        self.assertEqual(config["REVEAL_THEME"], "sky")

    def test_config_python_restricted_builtins(self):
        """Test that Python config files have restricted builtins"""
        config_file = Path(self.tests_folder) / "config.py"
        # Try to use a dangerous builtin that should be restricted
        config_file.write_text("""
import os  # This should fail with restricted builtins
REVEAL_THEME = "black"
""")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            # Should raise an error due to restricted import
            with self.assertRaises(ValueError):
                Config(str(config_file))

    def test_config_auto_detect_toml(self):
        """Test auto-detection of TOML format without extension"""
        config_file = Path(self.tests_folder) / "config"
        config_file.write_text("""
reveal_theme = "simple"
""")

        # Should auto-detect as TOML and load successfully
        config = Config(str(config_file))
        self.assertEqual(config["REVEAL_THEME"], "simple")

    def test_config_case_insensitive_keys(self):
        """Test that TOML keys are converted to uppercase"""
        config_file = Path(self.tests_folder) / "config.toml"
        config_file.write_text("""
reveal_theme = "white"
REVEAL_SLIDE_SEPARATOR = "==="
Reveal_Template = "custom.html"
""")

        config = Config(str(config_file))

        # All should be uppercase in the config
        self.assertEqual(config["REVEAL_THEME"], "white")
        self.assertEqual(config["REVEAL_SLIDE_SEPARATOR"], "===")
        self.assertEqual(config["REVEAL_TEMPLATE"], "custom.html")
