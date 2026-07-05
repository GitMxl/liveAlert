from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import DanmakuFetchResult, DanmakuMessage, LiveStatusResult, Streamer, utc_now_iso


class BilibiliAdapter(PlatformAdapter):
    name = "Bilibili"
    display_name = "Bilibili"

    _ROOM_INIT_API = "https://api.live.bilibili.com/room/v1/Room/room_init"
    _ROOM_INFO_API = "https://api.live.bilibili.com/room/v1/Room/get_info"
    _DANMAKU_HISTORY_API = "https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory"

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        raw_room = streamer.room_url.strip()
        room_ref = self.extract_room_id(raw_room)
        if not room_ref:
            return LiveStatusResult.error_result("Bilibili \u9700\u8981\u76f4\u64ad\u95f4\u94fe\u63a5\u6216\u623f\u95f4\u53f7")

        try:
            room_id = self._resolve_room_id(room_ref)
            payload = self._request_json(self._ROOM_INFO_API, {"room_id": room_id})
        except BilibiliRequestError as exc:
            return LiveStatusResult.error_result(str(exc))

        data = payload.get("data")
        if not isinstance(data, dict):
            return LiveStatusResult.error_result("Bilibili response missing data")

        live_status = self._to_int(data.get("live_status"))
        title = str(data.get("title") or "")
        resolved_room_id = str(data.get("room_id") or room_id)
        live_time = str(data.get("live_time") or "")

        if live_status == 1:
            live_id = f"bilibili:{resolved_room_id}:{live_time or title or 'live'}"
            return LiveStatusResult.live(title=title, live_id=live_id, detail=f"room_id={resolved_room_id}")
        if live_status == 0:
            return LiveStatusResult.offline(f"room_id={resolved_room_id}")
        if live_status == 2:
            return LiveStatusResult.offline(f"room_id={resolved_room_id}, round/replay")
        return LiveStatusResult.unknown(f"room_id={resolved_room_id}, live_status={live_status}")

    def build_watch_url(self, streamer: Streamer) -> str:
        room_id = self.extract_room_id(streamer.room_url.strip())
        if room_id:
            return f"https://live.bilibili.com/{room_id}"
        return streamer.room_url

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        room_ref = self.extract_room_id(streamer.room_url.strip())
        if not room_ref:
            return DanmakuFetchResult.error_result("Bilibili \u9700\u8981\u76f4\u64ad\u95f4\u94fe\u63a5\u6216\u623f\u95f4\u53f7")

        try:
            room_id = self._resolve_room_id(room_ref)
            payload = self._request_json(self._DANMAKU_HISTORY_API, {"roomid": room_id})
        except BilibiliRequestError as exc:
            return DanmakuFetchResult.error_result(str(exc))

        messages = self._messages_from_history(payload, room_id, since_id)
        detail = "" if messages else "\u6682\u65e0\u65b0\u5f39\u5e55"
        return DanmakuFetchResult.ok(messages, detail=detail)

    @classmethod
    def extract_room_id(cls, value: str) -> str:
        value = value.strip()
        if value.isdigit():
            return value

        parsed = urlparse(value)
        for part in parsed.path.split("/"):
            if part.isdigit():
                return part

        query_match = re.search(r"(?:room_id|id)=(\d+)", parsed.query)
        if query_match:
            return query_match.group(1)

        fallback_match = re.search(r"\b(\d{2,})\b", value)
        return fallback_match.group(1) if fallback_match else ""

    def _resolve_room_id(self, room_ref: str) -> str:
        payload = self._request_json(self._ROOM_INIT_API, {"id": room_ref})
        data = payload.get("data")
        if isinstance(data, dict) and data.get("room_id"):
            return str(data["room_id"])
        return room_ref

    def _request_json(self, url: str, params: dict[str, str]) -> dict:
        request_url = f"{url}?{urlencode(params)}"
        request = Request(
            request_url,
            headers={
                "User-Agent": "StreamerLiveMonitor/0.1 (+local desktop app)",
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://live.bilibili.com/",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise BilibiliRequestError(f"Bilibili HTTP {exc.code}") from exc
        except URLError as exc:
            raise BilibiliRequestError(f"Bilibili network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise BilibiliRequestError("Bilibili request timeout") from exc
        except OSError as exc:
            raise BilibiliRequestError(f"Bilibili request failed: {exc}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise BilibiliRequestError("Bilibili response is not JSON") from exc

        code = payload.get("code")
        if code not in (0, "0"):
            message = payload.get("message") or payload.get("msg") or "unknown error"
            raise BilibiliRequestError(f"Bilibili API error: {message}")
        return payload

    def _messages_from_history(self, payload: dict, room_id: str, since_id: str = "") -> list[DanmakuMessage]:
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        items: list[dict] = []
        for key in ("room", "admin"):
            value = data.get(key)
            if isinstance(value, list):
                items.extend(item for item in value if isinstance(item, dict))

        messages: list[DanmakuMessage] = []
        for item in items:
            content = str(item.get("text") or item.get("content") or item.get("msg") or "").strip()
            if not content:
                continue
            author = str(item.get("nickname") or item.get("uname") or item.get("user_name") or "").strip()
            sent_at = str(item.get("timeline") or item.get("time") or item.get("timestamp") or "").strip() or utc_now_iso()
            uid = str(item.get("uid") or item.get("user_id") or "").strip()
            message_id = str(item.get("id") or item.get("msg_id") or "").strip()
            if not message_id:
                message_id = f"bilibili:{room_id}:{sent_at}:{uid}:{author}:{content}"
            messages.append(DanmakuMessage(author=author, content=content, sent_at=sent_at, message_id=message_id))

        return self._messages_after(messages, since_id)

    @staticmethod
    def _messages_after(messages: list[DanmakuMessage], since_id: str) -> list[DanmakuMessage]:
        if not since_id:
            return messages[-100:]
        for index, message in enumerate(messages):
            if message.message_id == since_id:
                return messages[index + 1 :][-100:]
        return messages[-100:]

    @staticmethod
    def _to_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1


class BilibiliRequestError(Exception):
    pass
