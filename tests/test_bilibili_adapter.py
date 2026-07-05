import unittest

import _bootstrap  # noqa: F401

from live_monitor.adapters.bilibili import BilibiliAdapter
from live_monitor.models import Streamer


class BilibiliAdapterTest(unittest.TestCase):
    def test_extract_room_id_from_plain_number(self):
        self.assertEqual(BilibiliAdapter.extract_room_id("123456"), "123456")

    def test_extract_room_id_from_live_url(self):
        self.assertEqual(
            BilibiliAdapter.extract_room_id("https://live.bilibili.com/123456?spm_id_from=abc"),
            "123456",
        )

    def test_build_watch_url_from_room_id(self):
        streamer = Streamer(nickname="demo", platform="Bilibili", room_url="123456")
        self.assertEqual(BilibiliAdapter().build_watch_url(streamer), "https://live.bilibili.com/123456")


if __name__ == "__main__":
    unittest.main()
