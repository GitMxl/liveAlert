from __future__ import annotations

import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import LiveStatusResult, Streamer


class HuyaAdapter(PlatformAdapter):
    name = "\u864e\u7259"
    display_name = "\u864e\u7259"

    _ROOM_URL = "https://www.huya.com/{room_id}"

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        room_id = self.extract_room_id(streamer.room_url)
        if not room_id:
            return LiveStatusResult.error_result("\u864e\u7259\u9700\u8981\u76f4\u64ad\u95f4\u94fe\u63a5\u6216\u623f\u95f4\u53f7")

        try:
            html = self._request_text(self._ROOM_URL.format(room_id=room_id))
        except HuyaRequestError as exc:
            return LiveStatusResult.error_result(str(exc))

        title = self._extract_title(html)
        if self._looks_live(html):
            live_id = f"huya:{room_id}:{title or 'live'}"
            return LiveStatusResult.live(title=title, live_id=live_id, detail=f"room_id={room_id}")
        if self._looks_offline(html):
            return LiveStatusResult.offline(f"room_id={room_id}")
        return LiveStatusResult.unknown(f"room_id={room_id}, page unknown")

    def build_watch_url(self, streamer: Streamer) -> str:
        room_id = self.extract_room_id(streamer.room_url)
        if room_id:
            return self._ROOM_URL.format(room_id=room_id)
        return streamer.room_url

    @classmethod
    def extract_room_id(cls, value: str) -> str:
        value = value.strip()
        if value and "/" not in value and "?" not in value and not value.startswith(("http://", "https://")):
            return value

        parsed = urlparse(value)
        for part in parsed.path.split("/"):
            part = part.strip()
            if part:
                return part

        query_match = re.search(r"(?:room_id|id)=(\w+)", parsed.query)
        if query_match:
            return query_match.group(1)
        return ""

    def _request_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "StreamerLiveMonitor/0.1 (+local desktop app)",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Referer": "https://www.huya.com/",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                return response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise HuyaRequestError(f"Huya HTTP {exc.code}") from exc
        except URLError as exc:
            raise HuyaRequestError(f"Huya network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise HuyaRequestError("Huya request timeout") from exc
        except OSError as exc:
            raise HuyaRequestError(f"Huya request failed: {exc}") from exc

    @staticmethod
    def _looks_live(html: str) -> bool:
        patterns = [
            r'"isOn"\s*:\s*true',
            r'"isLive"\s*:\s*true',
            r'"liveStatus"\s*:\s*"?1"?',
            r'"isOn"\s*:\s*"?1"?',
        ]
        return any(re.search(pattern, html, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _looks_offline(html: str) -> bool:
        patterns = [
            r'"isOn"\s*:\s*false',
            r'"isLive"\s*:\s*false',
            r'"liveStatus"\s*:\s*"?0"?',
        ]
        words = [
            "\u672a\u5f00\u64ad",
            "\u4e3b\u64ad\u6b63\u5728\u8d76\u6765",
            "\u76f4\u64ad\u5df2\u7ed3\u675f",
        ]
        return any(re.search(pattern, html, flags=re.IGNORECASE) for pattern in patterns) or any(
            word in html for word in words
        )

    @staticmethod
    def _extract_title(html: str) -> str:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not title_match:
            return ""
        return re.sub(r"\s+", " ", unescape(title_match.group(1))).strip()


class HuyaRequestError(Exception):
    pass
