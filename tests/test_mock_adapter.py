import unittest

import _bootstrap  # noqa: F401

from live_monitor.adapters.mock import MockAdapter
from live_monitor.adapters.registry import create_default_registry
from live_monitor.models import STATUS_ERROR, STATUS_LIVE, STATUS_OFFLINE, Streamer


class MockAdapterTest(unittest.TestCase):
    def test_live_url_returns_live(self):
        streamer = Streamer(nickname="demo", platform="Mock", room_url="mock://live")
        result = MockAdapter().check_live_status(streamer)
        self.assertEqual(result.status, STATUS_LIVE)
        self.assertTrue(result.live_id)

    def test_offline_url_returns_offline(self):
        streamer = Streamer(nickname="demo", platform="Mock", room_url="mock://offline")
        result = MockAdapter().check_live_status(streamer)
        self.assertEqual(result.status, STATUS_OFFLINE)

    def test_fail_url_returns_error(self):
        streamer = Streamer(nickname="demo", platform="Mock", room_url="mock://fail")
        result = MockAdapter().check_live_status(streamer)
        self.assertEqual(result.status, STATUS_ERROR)

    def test_registry_contains_reserved_platforms(self):
        names = create_default_registry().names()
        platforms = [
            "Bilibili",
            "\u6296\u97f3",
            "\u5feb\u624b",
            "\u6597\u9c7c",
            "\u864e\u7259",
            "Twitch",
            "YouTube",
        ]
        for platform in platforms:
            self.assertIn(platform, names)


if __name__ == "__main__":
    unittest.main()
