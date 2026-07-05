from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import DanmakuFetchResult, DanmakuMessage, LiveStatusResult, Streamer, utc_now_iso


class GenericHttpAdapter(PlatformAdapter):
    name = "Generic HTTP"
    display_name = "Generic HTTP"

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        url = streamer.room_url.strip()
        if not url.startswith(("http://", "https://")):
            return LiveStatusResult.error_result("Generic HTTP \u9700\u8981 HTTP/HTTPS \u5730\u5740")

        request = Request(
            url,
            headers={
                "User-Agent": "StreamerLiveMonitor/0.1 (+local desktop app)",
                "Accept": "application/json,text/plain,*/*",
            },
        )

        try:
            with urlopen(request, timeout=8) as response:
                content_type = response.headers.get("content-type", "")
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            return LiveStatusResult.error_result(f"HTTP {exc.code}")
        except URLError as exc:
            return LiveStatusResult.error_result(str(exc.reason))
        except TimeoutError:
            return LiveStatusResult.error_result("\u8bf7\u6c42\u8d85\u65f6")
        except OSError as exc:
            return LiveStatusResult.error_result(str(exc))

        if "json" in content_type.lower() or body.lstrip().startswith(("{", "[")):
            result = self._from_json(body)
            if result:
                return result

        return self._from_text(body, streamer.remark)

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        options = self._parse_remark_options(streamer.remark)
        url = options.get("danmaku_url", "").strip() or streamer.room_url.strip()
        if not url.startswith(("http://", "https://")):
            return DanmakuFetchResult.unsupported_result(
                "Generic HTTP \u9700\u8981 HTTP/HTTPS \u5f39\u5e55\u5730\u5740\uff0c\u53ef\u5728\u5907\u6ce8\u586b\u5199 danmaku_url=..."
            )

        request = Request(
            url,
            headers={
                "User-Agent": "StreamerLiveMonitor/0.1 (+local desktop app)",
                "Accept": "application/json,text/plain,*/*",
            },
        )

        try:
            with urlopen(request, timeout=8) as response:
                content_type = response.headers.get("content-type", "")
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            return DanmakuFetchResult.error_result(f"HTTP {exc.code}")
        except URLError as exc:
            return DanmakuFetchResult.error_result(str(exc.reason))
        except TimeoutError:
            return DanmakuFetchResult.error_result("\u8bf7\u6c42\u8d85\u65f6")
        except OSError as exc:
            return DanmakuFetchResult.error_result(str(exc))

        if "json" in content_type.lower() or body.lstrip().startswith(("{", "[")):
            result = self._from_danmaku_json(body, since_id)
            if result:
                return result

        return self._from_danmaku_text(body, since_id)

    def _from_json(self, body: str) -> LiveStatusResult | None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None

        if isinstance(payload, list):
            payload = payload[0] if payload and isinstance(payload[0], dict) else {}
        if not isinstance(payload, dict):
            return None

        live_value = payload.get("live")
        status_value = str(payload.get("status", "")).strip().lower()
        title = str(payload.get("title", "") or payload.get("live_title", ""))
        live_id = str(payload.get("live_id", "") or payload.get("session_id", ""))
        detail = str(payload.get("detail", "") or payload.get("message", ""))

        if isinstance(live_value, bool):
            if live_value:
                return LiveStatusResult.live(title=title, live_id=live_id, detail=detail)
            return LiveStatusResult.offline(detail)

        live_words = {"live", "online", "streaming", "on", "\u76f4\u64ad\u4e2d", "\u5f00\u64ad"}
        offline_words = {"offline", "off", "closed", "not_live", "\u672a\u5f00\u64ad", "\u4e0b\u64ad"}
        unknown_words = {"unknown", "\u672a\u77e5"}

        if status_value in live_words:
            return LiveStatusResult.live(title=title, live_id=live_id, detail=detail)
        if status_value in offline_words:
            return LiveStatusResult.offline(detail)
        if status_value in unknown_words:
            return LiveStatusResult.unknown(detail)

        return None

    def _from_text(self, body: str, remark: str) -> LiveStatusResult:
        options = self._parse_remark_options(remark)
        live_keyword = options.get("live_keyword", "")
        offline_keyword = options.get("offline_keyword", "")

        if live_keyword and live_keyword in body:
            return LiveStatusResult.live(detail=f"\u547d\u4e2d live_keyword={live_keyword}")
        if offline_keyword and offline_keyword in body:
            return LiveStatusResult.offline(f"\u547d\u4e2d offline_keyword={offline_keyword}")
        return LiveStatusResult.unknown("\u672a\u80fd\u4ece\u54cd\u5e94\u4e2d\u8bc6\u522b\u76f4\u64ad\u72b6\u6001")

    def _from_danmaku_json(self, body: str, since_id: str) -> DanmakuFetchResult | None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None

        items = self._extract_message_items(payload)
        if not items:
            return DanmakuFetchResult.ok([], "\u672a\u5728 JSON \u4e2d\u627e\u5230\u5f39\u5e55\u5217\u8868")

        messages: list[DanmakuMessage] = []
        for item in items:
            message = self._message_from_item(item)
            if message:
                messages.append(message)
        return DanmakuFetchResult.ok(self._messages_after(messages, since_id))

    def _from_danmaku_text(self, body: str, since_id: str) -> DanmakuFetchResult:
        messages: list[DanmakuMessage] = []
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        for line in lines[-100:]:
            sent_at = utc_now_iso()
            author = ""
            content = line
            if "\t" in line:
                parts = [part.strip() for part in line.split("\t") if part.strip()]
                if len(parts) >= 3:
                    sent_at = self._normalize_sent_at(parts[0]) or sent_at
                    author = parts[1]
                    content = " ".join(parts[2:])
                elif len(parts) == 2:
                    author, content = parts
            elif ":" in line:
                author, content = [part.strip() for part in line.split(":", 1)]

            messages.append(
                DanmakuMessage(
                    author=author,
                    content=content,
                    sent_at=sent_at,
                    message_id=f"text:{line}",
                )
            )
        if not messages:
            return DanmakuFetchResult.ok([], "\u54cd\u5e94\u4e2d\u6ca1\u6709\u53ef\u663e\u793a\u7684\u5f39\u5e55\u884c")
        return DanmakuFetchResult.ok(self._messages_after(messages, since_id))

    def _extract_message_items(self, payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in ("danmaku", "messages", "comments", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("danmaku", "messages", "comments", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _message_from_item(self, item: Any) -> DanmakuMessage | None:
        if isinstance(item, str):
            content = item.strip()
            if not content:
                return None
            return DanmakuMessage(content=content, message_id=f"text:{content}")

        if not isinstance(item, dict):
            return None

        content = self._first_text(item, ("content", "text", "message", "comment", "body"))
        if not content:
            return None
        author = self._first_text(item, ("author", "user", "username", "nickname", "name"))
        sent_at = self._normalize_sent_at(
            self._first_existing(item, ("sent_at", "time", "timestamp", "created_at", "date"))
        )
        if not sent_at:
            sent_at = utc_now_iso()
        raw_id = self._first_existing(item, ("id", "message_id", "mid", "cid"))
        message_id = str(raw_id).strip() if raw_id is not None else ""
        if not message_id:
            message_id = f"json:{sent_at}:{author}:{content}"
        return DanmakuMessage(author=author, content=content, sent_at=sent_at, message_id=message_id)

    @staticmethod
    def _first_existing(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return value
        return None

    @classmethod
    def _first_text(cls, payload: dict[str, Any], keys: tuple[str, ...]) -> str:
        value = cls._first_existing(payload, keys)
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _normalize_sent_at(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            timestamp = float(value) / 1000 if float(value) > 1_000_000_000_000 else float(value)
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        text = str(value).strip()
        if text.isdigit():
            timestamp = float(text) / 1000 if len(text) >= 13 else float(text)
            return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        return text

    @staticmethod
    def _messages_after(messages: list[DanmakuMessage], since_id: str) -> list[DanmakuMessage]:
        if not since_id:
            return messages[-100:]
        for index, message in enumerate(messages):
            if message.message_id == since_id:
                return messages[index + 1 :][-100:]
        return messages[-100:]

    @staticmethod
    def _parse_remark_options(remark: str) -> dict[str, str]:
        options: dict[str, str] = {}
        for line in remark.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                options[key] = value
        return options
