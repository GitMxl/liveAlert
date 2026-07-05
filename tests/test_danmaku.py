import json
import unittest

import _bootstrap  # noqa: F401

from live_monitor.adapters.bilibili import BilibiliAdapter
from live_monitor.adapters.generic_http import GenericHttpAdapter
from live_monitor.adapters.mock import MockAdapter
from live_monitor.adapters.placeholder import ReservedPlatformAdapter
from live_monitor.adapters.twitch import TwitchAdapter
from live_monitor.adapters.youtube import YouTubeAdapter
from live_monitor.models import Streamer


class DanmakuTest(unittest.TestCase):
    def test_mock_adapter_returns_danmaku_message(self):
        streamer = Streamer(nickname="demo", platform="Mock", room_url="mock://live")
        result = MockAdapter().fetch_danmaku(streamer)

        self.assertFalse(result.error)
        self.assertFalse(result.unsupported)
        self.assertEqual(len(result.messages), 1)
        self.assertTrue(result.messages[0].message_id)
        self.assertTrue(result.messages[0].content)

    def test_mock_adapter_respects_since_id(self):
        streamer = Streamer(nickname="demo", platform="Mock", room_url="mock://live")
        adapter = MockAdapter()
        first = adapter.fetch_danmaku(streamer)
        second = adapter.fetch_danmaku(streamer, since_id=first.messages[0].message_id)

        self.assertEqual(second.messages, [])

    def test_generic_http_parses_json_messages(self):
        payload = {
            "messages": [
                {"id": "1", "author": "alice", "content": "hello", "timestamp": 1_700_000_000},
                {"id": "2", "nickname": "bob", "text": "world", "time": "2026-07-05T00:00:00+00:00"},
            ]
        }
        result = GenericHttpAdapter()._from_danmaku_json(json.dumps(payload), since_id="1")

        self.assertIsNotNone(result)
        self.assertEqual([message.content for message in result.messages], ["world"])
        self.assertEqual(result.messages[0].author, "bob")

    def test_generic_http_parses_text_lines(self):
        body = "alice: hello\n2026-07-05T00:00:00+00:00\tbob\tworld\n"
        result = GenericHttpAdapter()._from_danmaku_text(body, since_id="")

        self.assertEqual(len(result.messages), 2)
        self.assertEqual(result.messages[0].author, "alice")
        self.assertEqual(result.messages[1].content, "world")

    def test_default_adapter_reports_unsupported_danmaku(self):
        streamer = Streamer(nickname="demo", platform="Demo", room_url="demo")
        result = ReservedPlatformAdapter("Demo").fetch_danmaku(streamer)

        self.assertTrue(result.unsupported)
        self.assertIn("Demo", result.detail)

    def test_bilibili_parses_history_messages(self):
        payload = {
            "data": {
                "room": [
                    {"uid": 1, "nickname": "alice", "text": "hello", "timeline": "2026-07-05 12:00:00"},
                    {"uid": 2, "nickname": "bob", "text": "world", "timeline": "2026-07-05 12:00:01"},
                ]
            }
        }
        adapter = BilibiliAdapter()
        first = adapter._messages_from_history(payload, "123")
        second = adapter._messages_from_history(payload, "123", since_id=first[0].message_id)

        self.assertEqual([message.content for message in first], ["hello", "world"])
        self.assertEqual([message.author for message in second], ["bob"])

    def test_youtube_parses_live_chat_messages(self):
        payload = {
            "items": [
                {
                    "id": "yt-1",
                    "snippet": {"publishedAt": "2026-07-05T00:00:00Z", "displayMessage": "hello"},
                    "authorDetails": {"displayName": "alice"},
                },
                {
                    "id": "yt-2",
                    "snippet": {
                        "publishedAt": "2026-07-05T00:00:01Z",
                        "textMessageDetails": {"messageText": "world"},
                    },
                    "authorDetails": {"displayName": "bob"},
                },
            ]
        }
        messages = YouTubeAdapter()._messages_from_live_chat_payload(payload)

        self.assertEqual([message.content for message in messages], ["hello", "world"])
        self.assertEqual(messages[1].author, "bob")

    def test_twitch_parses_privmsg(self):
        line = (
            "@display-name=Alice;id=abc;tmi-sent-ts=1700000000000 "
            ":alice!alice@alice.tmi.twitch.tv PRIVMSG #openai :hello chat"
        )
        message = TwitchAdapter._parse_privmsg(line)

        self.assertIsNotNone(message)
        self.assertEqual(message.author, "Alice")
        self.assertEqual(message.content, "hello chat")
        self.assertEqual(message.message_id, "abc")

    def test_twitch_reads_chat_credentials_from_remark(self):
        credentials = TwitchAdapter._chat_credentials("chat_nick=demo\nchat_oauth=oauth:test")

        self.assertEqual(credentials, ("oauth:test", "demo"))


if __name__ == "__main__":
    unittest.main()
