from __future__ import annotations

from urllib.parse import urlparse

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import LiveStatusResult, Streamer


class ReservedPlatformAdapter(PlatformAdapter):
    def __init__(self, name: str, display_name: str | None = None) -> None:
        self.name = name
        self.display_name = display_name or name

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        return LiveStatusResult.unknown(
            f"{self.display_name} \u5df2\u652f\u6301\u4fdd\u5b58\u623f\u95f4\u53f7\u6216\u76f4\u64ad\u95f4\u94fe\u63a5\uff0c"
            "\u4f46\u771f\u5b9e\u68c0\u6d4b\u9700\u63a5\u5165\u5b98\u65b9 API\u3001"
            "\u516c\u5f00\u6388\u6743\u63a5\u53e3\u6216\u81ea\u6709\u5408\u89c4\u72b6\u6001\u670d\u52a1\u3002"
        )

    def build_watch_url(self, streamer: Streamer) -> str:
        value = streamer.room_url.strip()
        if value.startswith(("http://", "https://")):
            return value
        if not value:
            return value
        host = self._platform_host()
        return f"https://{host}/{value}" if host else value

    def _platform_host(self) -> str:
        hosts = {
            "Twitch": "www.twitch.tv",
            "YouTube": "www.youtube.com",
            "\u6597\u9c7c": "www.douyu.com",
            "\u864e\u7259": "www.huya.com",
        }
        return hosts.get(self.name, "")

    @staticmethod
    def _host_from_url(value: str) -> str:
        parsed = urlparse(value)
        return parsed.netloc
