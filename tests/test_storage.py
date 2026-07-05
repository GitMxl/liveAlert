import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from live_monitor.models import AppSettings, ReminderRecord, StatusLogRecord, Streamer
from live_monitor.storage import JsonStore


class JsonStoreTest(unittest.TestCase):
    def test_add_and_reload_streamer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = JsonStore(path)
            store.add_streamer(
                Streamer(
                    nickname="demo",
                    platform="Mock",
                    room_url="mock://live",
                    group="test",
                    favorite=True,
                )
            )

            reloaded = JsonStore(path)
            streamers = reloaded.list_streamers()

            self.assertEqual(len(streamers), 1)
            self.assertEqual(streamers[0].nickname, "demo")
            self.assertEqual(streamers[0].group, "test")
            self.assertTrue(streamers[0].favorite)

    def test_add_and_reload_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = JsonStore(path)
            store.add_history(
                ReminderRecord(
                    streamer_id="s1",
                    nickname="demo",
                    platform="Mock",
                    room_url="mock://live",
                    title="live",
                    live_session_id="session-1",
                )
            )

            reloaded = JsonStore(path)
            history = reloaded.list_history()

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].nickname, "demo")
            self.assertEqual(history[0].live_session_id, "session-1")

    def test_reload_settings_and_custom_interval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = JsonStore(path)
            store.update_settings(
                AppSettings(
                    check_interval_seconds=30,
                    title_change_notifications_enabled=False,
                    platform_configs={"Twitch": {"client_id": "cid"}, "YouTube": {"api_key": "key"}},
                )
            )
            store.add_streamer(
                Streamer(
                    nickname="demo",
                    platform="Mock",
                    room_url="mock://live",
                    custom_interval_seconds=120,
                )
            )

            reloaded = JsonStore(path)
            settings = reloaded.get_settings()
            streamers = reloaded.list_streamers()

            self.assertFalse(settings.title_change_notifications_enabled)
            self.assertEqual(settings.platform_configs["Twitch"]["client_id"], "cid")
            self.assertEqual(settings.platform_configs["YouTube"]["api_key"], "key")
            self.assertEqual(streamers[0].custom_interval_seconds, 120)

    def test_add_and_reload_status_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            store = JsonStore(path)
            store.add_status_log(
                StatusLogRecord(
                    streamer_id="s1",
                    nickname="demo",
                    platform="Mock",
                    room_url="mock://live",
                    event_type="title_changed",
                    old_title="old",
                    new_title="new",
                    message="changed",
                )
            )

            reloaded = JsonStore(path)
            logs = reloaded.list_status_logs()

            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].event_type, "title_changed")
            self.assertEqual(logs[0].old_title, "old")
            self.assertEqual(logs[0].new_title, "new")


if __name__ == "__main__":
    unittest.main()
