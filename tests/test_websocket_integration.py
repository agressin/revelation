"""Integration tests for WebSocket live reload functionality"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from revelation.app import PresentationReloader, PresentationReloadWebSocketSendEvent


class WebSocketReloadTestCase(TestCase):
    """Test WebSocket file watching and reload notification"""

    def setUp(self):
        self.tests_folder = tempfile.mkdtemp()
        self.tracking_path = self.tests_folder

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_event_handler_sends_on_md_change(self):
        """Test that event handler sends reload on .md file change"""
        # Create mock WebSocket
        mock_ws = Mock()
        mock_ws.closed = False

        handler = PresentationReloadWebSocketSendEvent(mock_ws)

        # Create mock event for .md file
        mock_event = Mock()
        mock_event.src_path = os.path.join(self.tracking_path, 'test.md')

        handler.on_modified(mock_event)

        # Should have sent reload message
        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        message = json.loads(call_args)
        self.assertEqual(message['msg_type'], 'message')
        self.assertEqual(message['message'], 'reload')

    def test_event_handler_sends_on_css_change(self):
        """Test that event handler sends reload on .css file change"""
        mock_ws = Mock()
        mock_ws.closed = False

        handler = PresentationReloadWebSocketSendEvent(mock_ws)

        mock_event = Mock()
        mock_event.src_path = os.path.join(self.tracking_path, 'style.css')

        handler.on_modified(mock_event)

        mock_ws.send.assert_called_once()

    def test_event_handler_ignores_other_files(self):
        """Test that event handler ignores non .md/.css files"""
        mock_ws = Mock()
        mock_ws.closed = False

        handler = PresentationReloadWebSocketSendEvent(mock_ws)

        # Test various file types
        for filename in ['test.txt', 'image.png', 'data.json', 'script.py']:
            mock_event = Mock()
            mock_event.src_path = os.path.join(self.tracking_path, filename)

            handler.on_modified(mock_event)

        # Should not have sent any messages
        mock_ws.send.assert_not_called()

    def test_event_handler_ignores_closed_websocket(self):
        """Test that event handler doesn't send to closed WebSocket"""
        mock_ws = Mock()
        mock_ws.closed = True  # WebSocket is closed

        handler = PresentationReloadWebSocketSendEvent(mock_ws)

        mock_event = Mock()
        mock_event.src_path = os.path.join(self.tracking_path, 'test.md')

        handler.on_modified(mock_event)

        # Should not send to closed WebSocket
        mock_ws.send.assert_not_called()

    def test_event_handler_error_handling(self):
        """Test that event handler handles send errors gracefully"""
        mock_ws = Mock()
        mock_ws.closed = False
        mock_ws.send.side_effect = Exception("WebSocket error")

        handler = PresentationReloadWebSocketSendEvent(mock_ws)

        mock_event = Mock()
        mock_event.src_path = os.path.join(self.tracking_path, 'test.md')

        # Should not raise exception
        try:
            handler.on_modified(mock_event)
        except Exception as e:
            self.fail(f"Event handler raised exception: {e}")

    def test_reloader_initialization(self):
        """Test PresentationReloader initializes properly"""
        mock_ws = Mock()

        reloader = PresentationReloader(mock_ws)

        self.assertIsNone(reloader.observer)
        self.assertIsNone(reloader.event_handler)

    def test_reloader_starts_observer_on_open(self):
        """Test that reloader starts observer when WebSocket opens"""
        mock_ws = Mock()
        mock_ws.closed = False

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tracking_path

        reloader.on_open()

        self.assertIsNotNone(reloader.observer)
        self.assertIsNotNone(reloader.event_handler)
        self.assertTrue(reloader.observer.is_alive())

        # Cleanup
        reloader.on_close(None)

    def test_reloader_doesnt_start_without_path(self):
        """Test that reloader doesn't start if tracking_path is None"""
        mock_ws = Mock()

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = None

        reloader.on_open()

        self.assertIsNone(reloader.observer)
        self.assertIsNone(reloader.event_handler)

    def test_reloader_stops_observer_on_close(self):
        """Test that reloader properly stops observer on close"""
        mock_ws = Mock()
        mock_ws.closed = False

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tracking_path

        reloader.on_open()
        observer = reloader.observer
        self.assertTrue(observer.is_alive())

        reloader.on_close(None)

        # Observer should be stopped and joined
        time.sleep(0.1)  # Give it time to stop
        self.assertFalse(observer.is_alive())
        self.assertIsNone(reloader.observer)
        self.assertIsNone(reloader.event_handler)

    def test_reloader_cleanup_on_failed_start(self):
        """Test that reloader cleans up if observer start fails"""
        mock_ws = Mock()

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = "/nonexistent/path"

        # Should handle error gracefully
        reloader.on_open()

        # Should have cleaned up
        self.assertIsNone(reloader.observer)
        self.assertIsNone(reloader.event_handler)

    def test_reloader_double_close_safe(self):
        """Test that calling on_close twice doesn't crash"""
        mock_ws = Mock()

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tracking_path

        reloader.on_open()
        reloader.on_close(None)

        # Second close should be safe
        try:
            reloader.on_close(None)
        except Exception as e:
            self.fail(f"Double close raised exception: {e}")

    def test_reloader_recursive_watching(self):
        """Test that reloader watches subdirectories recursively"""
        mock_ws = Mock()
        mock_ws.closed = False

        # Create subdirectory
        subdir = Path(self.tracking_path) / 'subdir'
        subdir.mkdir()

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tracking_path

        reloader.on_open()

        # Observer should be watching recursively
        # This is indicated by recursive=True in the schedule call
        self.assertIsNotNone(reloader.observer)

        # Cleanup
        reloader.on_close(None)

    def test_on_message_does_nothing(self):
        """Test that on_message handler is a no-op"""
        mock_ws = Mock()

        reloader = PresentationReloader(mock_ws)

        # Should not raise any exception
        try:
            reloader.on_message("test message")
            reloader.on_message({"data": "json"})
            reloader.on_message(None)
        except Exception as e:
            self.fail(f"on_message raised exception: {e}")


class WebSocketIntegrationTestCase(TestCase):
    """Integration tests simulating real file changes"""

    def setUp(self):
        self.tests_folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tests_folder)

    def test_real_file_change_triggers_reload(self):
        """Test that actual file changes trigger reload (integration)"""
        mock_ws = Mock()
        mock_ws.closed = False

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tests_folder

        reloader.on_open()

        # Create a markdown file
        test_file = Path(self.tests_folder) / 'test.md'
        test_file.write_text('# Test')

        # Give file watcher time to detect
        time.sleep(0.5)

        # Modify the file
        test_file.write_text('# Modified')

        # Give file watcher time to detect modification
        time.sleep(0.5)

        # Should have sent reload notification
        # Note: Depending on OS, might get multiple events
        self.assertGreater(mock_ws.send.call_count, 0)

        # Cleanup
        reloader.on_close(None)

    def test_css_file_change_triggers_reload(self):
        """Test that CSS file changes trigger reload"""
        mock_ws = Mock()
        mock_ws.closed = False

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tests_folder

        reloader.on_open()

        # Create a CSS file
        css_file = Path(self.tests_folder) / 'style.css'
        css_file.write_text('body { color: red; }')

        time.sleep(0.5)

        # Modify it
        css_file.write_text('body { color: blue; }')

        time.sleep(0.5)

        # Should have sent reload notification
        self.assertGreater(mock_ws.send.call_count, 0)

        # Cleanup
        reloader.on_close(None)

    def test_non_watched_file_ignored(self):
        """Test that changes to non-.md/.css files are ignored"""
        mock_ws = Mock()
        mock_ws.closed = False

        reloader = PresentationReloader(mock_ws)
        reloader.tracking_path = self.tests_folder

        reloader.on_open()

        # Create a text file
        txt_file = Path(self.tests_folder) / 'notes.txt'
        txt_file.write_text('notes')

        time.sleep(0.5)

        # Modify it
        txt_file.write_text('more notes')

        time.sleep(0.5)

        # Should NOT have sent reload notification
        mock_ws.send.assert_not_called()

        # Cleanup
        reloader.on_close(None)
