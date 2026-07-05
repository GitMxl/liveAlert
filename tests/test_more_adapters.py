import unittest

import _bootstrap  # noqa: F401

from live_monitor.adapters.huya import HuyaAdapter
from live_monitor.adapters.registry import create_default_registry
from live_monitor.adapters.twitch import TwitchAdapter
from live_monitor.adapters.youtube import YouTubeAdapter
from live_monitor.models import STATUS_UNKNOWN, Streamer


class MoreAdaptersTest(unittest.TestCase):
    def test_huya_extract_room_id_and_build_url(self):
        self.assertEqual(HuyaAdapter.extract_room_id("https://www.huya.com/abc123"), "abc123")
        streamer = Streamer(nickname="demo", platform="\u864e\u7259", room_url="abc123")
        self.assertEqual(HuyaAdapter().build_watch_url(streamer), "https://www.huya.com/abc123")

    def test_twitch_extract_channel_and_missing_credentials(self):
        self.assertEqual(TwitchAdapter.extract_channel("https://www.twitch.tv/openai"), "openai")
        streamer = Streamer(nickname="demo", platform="Twitch", room_url="openai")
        result = TwitchAdapter().check_live_status(streamer)
        self.assertEqual(result.status, STATUS_UNKNOWN)

    def test_youtube_extract_watch_video_and_missing_key(self):
        target = YouTubeAdapter.extract_target("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(target.video_id, "dQw4w9WgXcQ")
        streamer = Streamer(nickname="demo", platform="YouTube", room_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        result = YouTubeAdapter().check_live_status(streamer)
        self.assertEqual(result.status, STATUS_UNKNOWN)

    def test_registry_uses_real_adapter_entries(self):
        registry = create_default_registry()
        self.assertIsInstance(registry.get("\u864e\u7259"), HuyaAdapter)
        self.assertIsInstance(registry.get("Twitch"), TwitchAdapter)
        self.assertIsInstance(registry.get("YouTube"), YouTubeAdapter)


if __name__ == "__main__":
    unittest.main()
