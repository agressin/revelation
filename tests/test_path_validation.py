"""Tests for path validation security"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from revelation import Revelation


class PathValidationTestCase(TestCase):
    def setUp(self):
        self.tests_folder = tempfile.mkdtemp()
        self.media = tempfile.mkdtemp(dir=self.tests_folder)
        _, self.slide = tempfile.mkstemp(".md", dir=self.tests_folder)

        with open(self.slide, "w") as f:
            f.write("# Test\n---\n# Page 2")

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_valid_presentation_path(self):
        """Test that valid presentation path is accepted"""
        app = Revelation(self.slide)
        self.assertIsNotNone(app.presentation)
        self.assertTrue(os.path.isabs(app.presentation))

    def test_valid_media_path(self):
        """Test that valid media path is accepted"""
        app = Revelation(self.slide, media=self.media)
        # Should initialize without errors
        self.assertIsNotNone(app)

    def test_path_traversal_rejected(self):
        """Test that path traversal attempts are rejected"""
        malicious_path = os.path.join(self.tests_folder, "..", "..", "etc", "passwd")

        with self.assertRaises(ValueError) as context:
            Revelation(self.slide, media=malicious_path)

        self.assertIn("Path traversal", str(context.exception))

    def test_relative_path_with_dotdot_rejected(self):
        """Test that relative paths with .. are rejected"""
        with self.assertRaises(ValueError) as context:
            Revelation(self.slide, theme="../../../etc")

        self.assertIn("Path traversal", str(context.exception))

    def test_nonexistent_media_path_warning(self):
        """Test that non-existent media path generates warning but doesn't crash"""
        nonexistent = os.path.join(self.tests_folder, "does_not_exist")

        # Should not raise, but may warn
        app = Revelation(self.slide, media=nonexistent)
        self.assertIsNotNone(app)

    def test_file_instead_of_directory_warning(self):
        """Test warning when media path points to file instead of directory"""
        # Create a file
        _, file_path = tempfile.mkstemp(dir=self.tests_folder)

        # Should handle gracefully
        app = Revelation(self.slide, media=file_path)
        self.assertIsNotNone(app)

    def test_absolute_paths_resolved(self):
        """Test that absolute paths are properly resolved"""
        app = Revelation(self.slide, media=self.media)
        # Paths should be absolute after validation
        self.assertTrue(os.path.isabs(app.presentation))

    def test_style_file_validation(self):
        """Test that style file must exist and be a file"""
        # Create a valid CSS file
        _, style_file = tempfile.mkstemp(".css", dir=self.tests_folder)
        with open(style_file, "w") as f:
            f.write("body { color: red; }")

        app = Revelation(self.slide, style=style_file)
        self.assertIsNotNone(app.style)

    def test_style_directory_rejected(self):
        """Test that style path cannot be a directory"""
        # Try to use directory as style
        style_dir = tempfile.mkdtemp(dir=self.tests_folder)

        # Should handle gracefully (warning, not crash)
        app = Revelation(self.slide, style=style_dir)
        # Style should be None since validation failed
        self.assertIsNone(app.style)

    def test_symlink_handling(self):
        """Test that symlinks are handled safely"""
        # Create a symlink
        target_dir = tempfile.mkdtemp(dir=self.tests_folder)
        symlink_path = os.path.join(self.tests_folder, "media_link")

        try:
            os.symlink(target_dir, symlink_path)
        except OSError:
            # Skip test on systems that don't support symlinks
            self.skipTest("System doesn't support symlinks")

        # Should resolve symlink to real path
        app = Revelation(self.slide, media=symlink_path)
        self.assertIsNotNone(app)

    def test_validate_path_static_method(self):
        """Test _validate_path static method directly"""
        # Valid path
        valid = Revelation._validate_path(self.tests_folder, "test")
        self.assertIsNotNone(valid)
        self.assertTrue(os.path.isabs(valid))

        # Path traversal
        with self.assertRaises(ValueError):
            Revelation._validate_path("../../etc/passwd", "test")

        # None path
        result = Revelation._validate_path(None, "test")
        self.assertIsNone(result)

        # Empty string
        result = Revelation._validate_path("", "test")
        self.assertIsNone(result)
