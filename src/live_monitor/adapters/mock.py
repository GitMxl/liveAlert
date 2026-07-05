from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import DanmakuFetchResult, DanmakuMessage, LiveStatusResult, Streamer


class MockAdapter(PlatformAdapter):
    name = "Mock"
    display_name = "Mock"

    DANMAKU_CONTENTS = (
        "\u6765\u4e86\u6765\u4e86",
        "\u8fd9\u6ce2\u5f88\u7a33",
        "\u4e3b\u64ad\u665a\u4e0a\u597d",
        "\u5f39\u5e55\u529f\u80fd\u6d4b\u8bd5",
        "\u8fd9\u4e2a\u754c\u9762\u53ef\u4ee5",
        "\u5237\u65b0\u4e00\u4e0b\u770b\u770b",
    )

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        parsed = urlparse(streamer.room_url.strip())
        target = (parsed.netloc or parsed.path).lower()

        if target in {"live", "always-live"}:
            return LiveStatusResult.live(
                title="Mock \u76f4\u64ad\u95f4\u6b63\u5728\u76f4\u64ad",
                live_id=f"{streamer.id}:mock-always-live",
                detail="mock://live",
            )

        if target in {"offline", "always-offline"}:
            return LiveStatusResult.offline("mock://offline")

        if target in {"fail", "error"}:
            return LiveStatusResult.error_result("Mock \u5e73\u53f0\u6a21\u62df\u68c0\u6d4b\u5931\u8d25")

        if target == "toggle":
            query = parse_qs(parsed.query)
            period = self._parse_period(query.get("period", ["60"])[0])
            current_slot = int(time.time() // period)
            in_live_window = time.time() % period < period / 2

            if in_live_window:
                return LiveStatusResult.live(
                    title=f"Mock \u5468\u671f\u5f00\u64ad #{current_slot}",
                    live_id=f"{streamer.id}:mock-toggle:{current_slot}",
                    detail=f"\u5468\u671f {period} \u79d2",
                )
            return LiveStatusResult.offline(f"\u5468\u671f {period} \u79d2\uff0c\u5f53\u524d\u672a\u5f00\u64ad")

        return LiveStatusResult.unknown(
            "\u8bf7\u4f7f\u7528 mock://live\u3001mock://offline\u3001mock://toggle?period=60 \u6216 mock://fail"
        )

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        parsed = urlparse(streamer.room_url.strip())
        target = (parsed.netloc or parsed.path).lower()

        if target in {"fail", "error"}:
            return DanmakuFetchResult.error_result("Mock \u5e73\u53f0\u6a21\u62df\u5f39\u5e55\u83b7\u53d6\u5931\u8d25")
        if target in {"offline", "always-offline"}:
            return DanmakuFetchResult.ok([], "Mock \u4e3b\u64ad\u672a\u5f00\u64ad\uff0c\u6682\u65e0\u5f39\u5e55")
        if target == "toggle":
            query = parse_qs(parsed.query)
            period = self._parse_period(query.get("period", ["60"])[0])
            if time.time() % period >= period / 2:
                return DanmakuFetchResult.ok([], "Mock \u5468\u671f\u5f53\u524d\u4e3a\u672a\u5f00\u64ad")

        slot = int(time.time() // 4)
        message_id = f"{streamer.id}:mock-danmaku:{slot}"
        if message_id == since_id:
            return DanmakuFetchResult.ok([], "\u5df2\u662f\u6700\u65b0\u5f39\u5e55")

        content = self.DANMAKU_CONTENTS[slot % len(self.DANMAKU_CONTENTS)]
        message = DanmakuMessage(
            author=f"\u89c2\u4f17{slot % 9 + 1}",
            content=content,
            message_id=message_id,
        )
        return DanmakuFetchResult.ok([message])

    @staticmethod
    def _parse_period(raw_value: str) -> int:
        try:
            return max(20, int(raw_value))
        except ValueError:
            return 60
