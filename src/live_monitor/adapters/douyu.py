from __future__ import annotations

import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import LiveStatusResult, Streamer


class DouyuAdapter(PlatformAdapter):
    name = "\u6597\u9c7c"
    display_name = "\u6597\u9c7c"

    _ROOM_API = "https://open.douyucdn.cn/api/RoomApi/room/{room_id}"
    _ROOM_URL = "https://www.douyu.com/{room_id}"

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        room_id = self.extract_room_id(streamer.room_url)
        if not room_id:
            return LiveStatusResult.error_result("\u6597\u9c7c\u9700\u8981\u76f4\u64ad\u95f4\u94fe\u63a5\u6216\u623f\u95f4\u53f7")

        try:
            return self._check_with_room_api(room_id)
        except DouyuRequestError as api_error:
            page_result = self._check_with_room_page(room_id, str(api_error))
            if page_result:
                return page_result
            return LiveStatusResult.error_result(str(api_error))

    def build_watch_url(self, streamer: Streamer) -> str:
        room_id = self.extract_room_id(streamer.room_url)
        if room_id:
            return self._ROOM_URL.format(room_id=room_id)
        return streamer.room_url

    @classmethod
    def extract_room_id(cls, value: str) -> str:
        value = value.strip()
        if value.isdigit():
            return value

        parsed = urlparse(value)
        for part in parsed.path.split("/"):
            if part.isdigit():
                return part

        query_match = re.search(r"(?:room_id|rid|id)=(\d+)", parsed.query)
        if query_match:
            return query_match.group(1)

        fallback_match = re.search(r"\b(\d{2,})\b", value)
        return fallback_match.group(1) if fallback_match else ""

    def _check_with_room_api(self, room_id: str) -> LiveStatusResult:
        payload = self._request_json(self._ROOM_API.format(room_id=room_id))
        error_code = payload.get("error")
        if error_code not in (0, "0"):
            message = payload.get("msg") or payload.get("message") or "unknown error"
            raise DouyuRequestError(f"Douyu API error: {message}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise DouyuRequestError("Douyu API response missing data")

        status_value = str(data.get("room_status", "")).strip()
        resolved_room_id = str(data.get("room_id") or room_id)
        room_name = str(data.get("room_name") or "")
        owner_name = str(data.get("owner_name") or "")
        start_time = str(data.get("start_time") or "")

        if status_value == "1":
            live_id = f"douyu:{resolved_room_id}:{start_time or room_name or 'live'}"
            detail = self._detail(resolved_room_id, owner_name)
            return LiveStatusResult.live(title=room_name, live_id=live_id, detail=detail)

        if status_value in {"0", "2", "3", "4"}:
            return LiveStatusResult.offline(self._detail(resolved_room_id, owner_name))

        return LiveStatusResult.unknown(
            f"{self._detail(resolved_room_id, owner_name)}, room_status={status_value or 'empty'}"
        )

    def _check_with_room_page(self, room_id: str, reason: str) -> LiveStatusResult | None:
        try:
            html = self._request_text(self._ROOM_URL.format(room_id=room_id))
        except DouyuRequestError:
            return None

        page_title = self._extract_page_title(html)

        if self._looks_live(html):
            live_id = f"douyu:{room_id}:{page_title or 'live'}"
            return LiveStatusResult.live(title=page_title, live_id=live_id, detail=f"room_id={room_id}, page fallback")

        if self._looks_offline(html):
            return LiveStatusResult.offline(f"room_id={room_id}, page fallback")

        return LiveStatusResult.unknown(f"room_id={room_id}, page fallback unknown; api={reason}")

    def _request_json(self, url: str) -> dict:
        body = self._request_text(url, accept="application/json,text/plain,*/*")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DouyuRequestError("Douyu response is not JSON") from exc
        if not isinstance(payload, dict):
            raise DouyuRequestError("Douyu response is not an object")
        return payload

    def _request_text(self, url: str, accept: str = "text/html,application/xhtml+xml,*/*") -> str:
        request = Request(
            url,
            headers={
                "User-Agent": "StreamerLiveMonitor/0.1 (+local desktop app)",
                "Accept": accept,
                "Referer": "https://www.douyu.com/",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                return response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise DouyuRequestError(f"Douyu HTTP {exc.code}") from exc
        except URLError as exc:
            raise DouyuRequestError(f"Douyu network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise DouyuRequestError("Douyu request timeout") from exc
        except OSError as exc:
            raise DouyuRequestError(f"Douyu request failed: {exc}") from exc

    @staticmethod
    def _looks_live(html: str) -> bool:
        live_patterns = [
            r'"room_status"\s*:\s*"?1"?',
            r'"show_status"\s*:\s*"?1"?',
            r'"isLive"\s*:\s*true',
            r'"is_live"\s*:\s*"?1"?',
        ]
        return any(re.search(pattern, html, flags=re.IGNORECASE) for pattern in live_patterns)

    @staticmethod
    def _looks_offline(html: str) -> bool:
        offline_patterns = [
            r'"room_status"\s*:\s*"?2"?',
            r'"show_status"\s*:\s*"?2"?',
            r'"isLive"\s*:\s*false',
            r'"is_live"\s*:\s*"?0"?',
        ]
        offline_words = [
            "\u672a\u5f00\u64ad",
            "\u4e3b\u64ad\u6b63\u5728\u8d76\u6765",
            "\u76f4\u64ad\u5df2\u7ed3\u675f",
            "\u4e3b\u64ad\u6682\u65f6\u4e0d\u5728",
        ]
        return any(re.search(pattern, html, flags=re.IGNORECASE) for pattern in offline_patterns) or any(
            word in html for word in offline_words
        )

    @staticmethod
    def _extract_page_title(html: str) -> str:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not title_match:
            return ""
        title = re.sub(r"\s+", " ", unescape(title_match.group(1))).strip()
        return title

    @staticmethod
    def _detail(room_id: str, owner_name: str) -> str:
        if owner_name:
            return f"room_id={room_id}, owner={owner_name}"
        return f"room_id={room_id}"


class DouyuRequestError(Exception):
    pass
