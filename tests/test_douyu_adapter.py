import unittest

import _bootstrap  # noqa: F401

from live_monitor.adapters.douyu import DouyuAdapter
from live_monitor.adapters.registry import create_default_registry
from live_monitor.models import Streamer


class DouyuAdapterTest(unittest.TestCase):
    def test_extract_room_id_from_plain_number(self):
        self.assertEqual(DouyuAdapter.extract_room_id("475252"), "475252")

    def test_extract_room_id_from_live_url(self):
        self.assertEqual(DouyuAdapter.extract_room_id("https://www.douyu.com/475252"), "475252")

    def test_build_watch_url_from_room_id(self):
        streamer = Streamer(nickname="demo", platform="\u6597\u9c7c", room_url="475252")
        self.assertEqual(DouyuAdapter().build_watch_url(streamer), "https://www.douyu.com/475252")

    def test_registry_uses_douyu_adapter(self):
        adapter = create_default_registry().get("\u6597\u9c7c")
        self.assertIsInstance(adapter, DouyuAdapter)


if __name__ == "__main__":
    unittest.main()
