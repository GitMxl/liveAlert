from __future__ import annotations

from abc import ABC, abstractmethod

from live_monitor.models import DanmakuFetchResult, LiveStatusResult, Streamer


class PlatformAdapter(ABC):
    name: str
    display_name: str

    @abstractmethod
    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        raise NotImplementedError

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        return DanmakuFetchResult.unsupported_result(
            f"{self.display_name} \u6682\u672a\u63a5\u5165\u5f39\u5e55\u63a5\u53e3"
        )
