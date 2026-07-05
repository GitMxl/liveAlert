import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.adapters.registry import AdapterRegistry
from live_monitor.models import STATUS_ERROR, STATUS_LIVE, AppSettings, LiveStatusResult, Streamer, utc_now_iso
from live_monitor.monitor import MonitorService
from live_monitor.storage import JsonStore


class StaticAdapter(PlatformAdapter):
    name = "Fake"
    display_name = "Fake"

    def __init__(self, result: LiveStatusResult) -> None:
        self.result = result

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        return self.result


class RecordingAdapter(PlatformAdapter):
    name = "Fake"
    display_name = "Fake"

    def __init__(self, result: LiveStatusResult) -> None:
        self.result = result
        self.calls: list[Streamer] = []

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        self.calls.append(streamer)
        return self.result


class MonitorServiceTest(unittest.TestCase):
    def test_check_selected_updates_only_selected_streamer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            first = Streamer(nickname="first", platform="Fake", room_url="fake://1")
            second = Streamer(nickname="second", platform="Fake", room_url="fake://2")
            store.add_streamer(first)
            store.add_streamer(second)
            monitor = MonitorService(store, AdapterRegistry([StaticAdapter(LiveStatusResult.live(live_id="fake-live"))]))

            monitor.check_streamer(first.id)
            streamers = {streamer.id: streamer for streamer in store.list_streamers()}

            self.assertEqual(streamers[first.id].status, STATUS_LIVE)
            self.assertNotEqual(streamers[second.id].status, STATUS_LIVE)

    def test_error_result_sets_backoff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            streamer = Streamer(nickname="first", platform="Fake", room_url="fake://1")
            store.add_streamer(streamer)
            monitor = MonitorService(store, AdapterRegistry([StaticAdapter(LiveStatusResult.error_result("boom"))]))

            monitor.check_once()
            updated = store.list_streamers()[0]

            self.assertEqual(updated.status, STATUS_ERROR)
            self.assertEqual(updated.consecutive_failures, 1)
            self.assertTrue(updated.next_check_after)

    def test_custom_interval_skips_scheduled_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            streamer = Streamer(
                nickname="first",
                platform="Fake",
                room_url="fake://1",
                last_checked_at=utc_now_iso(),
                custom_interval_seconds=3600,
            )
            store.add_streamer(streamer)
            adapter = RecordingAdapter(LiveStatusResult.live(live_id="fake-live"))
            monitor = MonitorService(store, AdapterRegistry([adapter]))

            monitor.check_once()
            updated = store.list_streamers()[0]

            self.assertEqual(adapter.calls, [])
            self.assertNotEqual(updated.status, STATUS_LIVE)

    def test_live_title_change_adds_log_and_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            streamer = Streamer(
                nickname="first",
                platform="Fake",
                room_url="fake://1",
                status=STATUS_LIVE,
                live_title="old title",
                live_session_id="session-1",
                last_notified_session_id="session-1",
            )
            store.add_streamer(streamer)
            monitor = MonitorService(store, AdapterRegistry([StaticAdapter(LiveStatusResult.live(title="new title", live_id="session-1"))]))

            monitor.check_once()
            events = []
            while not monitor.events.empty():
                events.append(monitor.events.get())
            updated = store.list_streamers()[0]
            logs = store.list_status_logs()

            self.assertEqual(updated.live_title, "new title")
            self.assertTrue(any(event.kind == "title_changed" and event.message == "old title" for event in events))
            self.assertEqual(logs[-1].event_type, "title_changed")
            self.assertEqual(logs[-1].old_title, "old title")
            self.assertEqual(logs[-1].new_title, "new title")

    def test_platform_config_is_appended_to_adapter_remark(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonStore(Path(temp_dir) / "state.json")
            store.update_settings(AppSettings(platform_configs={"Fake": {"token": "abc"}}))
            streamer = Streamer(nickname="first", platform="Fake", room_url="fake://1", remark="room=one")
            store.add_streamer(streamer)
            adapter = RecordingAdapter(LiveStatusResult.offline())
            monitor = MonitorService(store, AdapterRegistry([adapter]))

            monitor.check_once()

            self.assertEqual(len(adapter.calls), 1)
            self.assertIn("room=one", adapter.calls[0].remark)
            self.assertIn("token=abc", adapter.calls[0].remark)


if __name__ == "__main__":
    unittest.main()
