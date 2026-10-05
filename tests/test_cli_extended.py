"""Extended tests for CLI commands"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from revelation.cli import cli


class CliExtendedTestCase(TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.tests_folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_version_flag(self):
        """Test --version flag"""
        result = self.runner.invoke(cli, ['--version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('1.1.0', result.output)

    def test_help_command(self):
        """Test help output"""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('start', result.output)
        self.assertIn('mkpresentation', result.output)
        self.assertIn('convertconfig', result.output)

    def test_mkpresentation_creates_structure(self):
        """Test that mkpresentation creates proper structure"""
        pres_path = os.path.join(self.tests_folder, 'test_pres')
        result = self.runner.invoke(cli, ['mkpresentation', pres_path])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.isdir(pres_path))
        self.assertTrue(os.path.isdir(os.path.join(pres_path, 'media')))
        self.assertTrue(os.path.isfile(os.path.join(pres_path, 'config.py')))
        self.assertTrue(os.path.isfile(os.path.join(pres_path, 'slides.md')))

    def test_mkpresentation_existing_dir_fails(self):
        """Test that mkpresentation fails if directory exists"""
        pres_path = os.path.join(self.tests_folder, 'existing')
        os.makedirs(pres_path)

        result = self.runner.invoke(cli, ['mkpresentation', pres_path])
        self.assertEqual(result.exit_code, 1)
        self.assertIn('already exists', result.output)

    def test_convertconfig_python_to_toml(self):
        """Test config conversion from Python to TOML"""
        # Create a Python config
        py_config = Path(self.tests_folder) / 'config.py'
        py_config.write_text("""
REVEAL_THEME = "black"
REVEAL_META = {
    "title": "Test",
    "author": "Tester"
}
""")

        result = self.runner.invoke(cli, [
            'convertconfig',
            str(py_config)
        ])

        self.assertEqual(result.exit_code, 0)
        toml_config = Path(self.tests_folder) / 'config.toml'
        self.assertTrue(toml_config.exists())

        # Check TOML content
        content = toml_config.read_text()
        self.assertIn('reveal_theme = "black"', content)
        self.assertIn('[reveal_meta]', content)
        self.assertIn('title = "Test"', content)

    def test_convertconfig_nonexistent_file(self):
        """Test conversion with non-existent file"""
        result = self.runner.invoke(cli, [
            'convertconfig',
            '/nonexistent/config.py'
        ])

        self.assertEqual(result.exit_code, 1)
        self.assertIn('not found', result.output)

    def test_convertconfig_with_output_option(self):
        """Test conversion with custom output file"""
        py_config = Path(self.tests_folder) / 'config.py'
        py_config.write_text('REVEAL_THEME = "moon"')

        output_file = Path(self.tests_folder) / 'custom.toml'
        result = self.runner.invoke(cli, [
            'convertconfig',
            str(py_config),
            '--output',
            str(output_file)
        ])

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(output_file.exists())
        self.assertIn('moon', output_file.read_text())

    def test_convertconfig_force_overwrite(self):
        """Test conversion with --force flag"""
        py_config = Path(self.tests_folder) / 'config.py'
        py_config.write_text('REVEAL_THEME = "sky"')

        toml_config = Path(self.tests_folder) / 'config.toml'
        toml_config.write_text('old content')

        # Without force should fail
        result = self.runner.invoke(cli, [
            'convertconfig',
            str(py_config)
        ])
        self.assertEqual(result.exit_code, 1)

        # With force should succeed
        result = self.runner.invoke(cli, [
            'convertconfig',
            str(py_config),
            '--force'
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('sky', toml_config.read_text())

    def test_start_with_nonexistent_presentation(self):
        """Test start command with non-existent presentation"""
        with patch('revelation.cli.os.path.exists', return_value=True):
            result = self.runner.invoke(cli, [
                'start',
                '/nonexistent/presentation'
            ])

            self.assertEqual(result.exit_code, 1)
            self.assertIn('not found', result.output.lower())

    def test_start_with_empty_directory(self):
        """Test start command with directory containing no .md files"""
        empty_dir = Path(self.tests_folder) / 'empty'
        empty_dir.mkdir()

        with patch('revelation.cli.os.path.exists', return_value=True):
            result = self.runner.invoke(cli, [
                'start',
                str(empty_dir)
            ])

            self.assertEqual(result.exit_code, 1)
            self.assertIn('No markdown files', result.output)

    def test_installreveal_command(self):
        """installreveal installe la version figée via install_revealjs"""
        with patch('revelation.cli.install_revealjs') as mock_install:
            mock_install.return_value = '5.2.1'
            result = self.runner.invoke(cli, ['installreveal'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('installed reveal.js', result.output.lower())
            mock_install.assert_called_once()
            self.assertEqual(mock_install.call_args.kwargs['version'], '5.2.1')

    def test_installreveal_error_is_reported(self):
        """une erreur de téléchargement donne un message, pas un traceback"""
        with patch('revelation.cli.install_revealjs', side_effect=RuntimeError('boom')):
            result = self.runner.invoke(cli, ['installreveal'])
            self.assertEqual(result.exit_code, 1)
            self.assertIn('boom', result.output)

    def test_start_without_revealjs_does_not_download(self):
        """start sans reveal.js : message clair, aucun téléchargement"""
        with patch('revelation.cli.os.path.exists', return_value=False):
            with patch('revelation.cli.install_revealjs') as mock_install:
                result = self.runner.invoke(cli, ['start', '.'])
                self.assertEqual(result.exit_code, 1)
                self.assertIn('bootstrap', result.output)
                mock_install.assert_not_called()


class CliErrorMessagesTestCase(TestCase):
    """Test that CLI provides helpful error messages"""

    def setUp(self):
        self.runner = CliRunner()
        self.tests_folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_helpful_error_no_md_files(self):
        """Test helpful error when no .md files in directory"""
        empty_dir = Path(self.tests_folder) / 'empty'
        empty_dir.mkdir()

        with patch('revelation.cli.os.path.exists', return_value=True):
            result = self.runner.invoke(cli, ['start', str(empty_dir)])

            # Should suggest creating presentation
            self.assertIn('mkpresentation', result.output)
            self.assertIn('markdown files', result.output.lower())

    def test_helpful_error_style_not_css(self):
        """Test helpful error for non-CSS style file"""
        # Create presentation
        pres_dir = Path(self.tests_folder) / 'pres'
        pres_dir.mkdir()
        (pres_dir / 'slides.md').write_text('# Test')

        # Create non-CSS file
        style_file = pres_dir / 'style.txt'
        style_file.write_text('not css')

        with patch('revelation.cli.os.path.exists', return_value=True):
            result = self.runner.invoke(cli, [
                'start',
                str(pres_dir),
                '--style',
                str(style_file)
            ])

            self.assertIn('.css', result.output)
            self.assertEqual(result.exit_code, 1)

    def test_port_in_use_error(self):
        """Test error message when port is already in use"""
        pres_dir = Path(self.tests_folder) / 'pres'
        pres_dir.mkdir()
        (pres_dir / 'slides.md').write_text('# Test')

        with patch('revelation.cli.os.path.exists', return_value=True):
            with patch('revelation.cli.Revelation'):
                with patch('revelation.cli.WebSocketServer') as mock_server:
                    # Simulate port in use error
                    mock_server.return_value.serve_forever.side_effect = OSError(
                        "Address already in use"
                    )

                    result = self.runner.invoke(cli, [
                        'start',
                        str(pres_dir),
                        '--port',
                        '4000'
                    ])

                    self.assertIn('already in use', result.output)
                    self.assertIn('4001', result.output)  # Suggests next port
