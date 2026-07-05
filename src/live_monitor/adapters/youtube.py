from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import DanmakuFetchResult, DanmakuMessage, LiveStatusResult, Streamer


class YouTubeAdapter(PlatformAdapter):
    name = "YouTube"
    display_name = "YouTube"

    _VIDEOS_API = "https://www.googleapis.com/youtube/v3/videos"
    _SEARCH_API = "https://www.googleapis.com/youtube/v3/search"
    _LIVE_CHAT_MESSAGES_API = "https://www.googleapis.com/youtube/v3/liveChat/messages"
    _WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
    _CHANNEL_URL = "https://www.youtube.com/channel/{channel_id}/live"

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        target = self.extract_target(streamer.room_url, streamer.remark)
        api_key = self._api_key(streamer.remark)
        if not api_key:
            return LiveStatusResult.unknown("YouTube Data API requires YOUTUBE_API_KEY or remark api_key")

        try:
            if target.video_id:
                return self._check_video(target.video_id, api_key)
            if target.channel_id:
                return self._check_channel(target.channel_id, api_key)
        except YouTubeRequestError as exc:
            return LiveStatusResult.error_result(str(exc))

        return LiveStatusResult.unknown("YouTube needs a video ID, channel ID, or remark channel_id")

    def build_watch_url(self, streamer: Streamer) -> str:
        target = self.extract_target(streamer.room_url, streamer.remark)
        if target.video_id:
            return self._WATCH_URL.format(video_id=target.video_id)
        if target.channel_id:
            return self._CHANNEL_URL.format(channel_id=target.channel_id)
        return streamer.room_url

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        target = self.extract_target(streamer.room_url, streamer.remark)
        api_key = self._api_key(streamer.remark)
        if not api_key:
            return DanmakuFetchResult.unsupported_result("YouTube \u5f39\u5e55\u9700\u8981 YOUTUBE_API_KEY \u6216\u5907\u6ce8 api_key")

        options = _parse_options(streamer.remark)
        try:
            live_chat_id = options.get("live_chat_id") or options.get("chat_id") or self._resolve_live_chat_id(target, api_key)
            if not live_chat_id:
                return DanmakuFetchResult.ok([], "YouTube \u76f4\u64ad\u804a\u5929\u4e0d\u53ef\u7528\uff0c\u53ef\u80fd\u672a\u5f00\u64ad\u6216\u5df2\u5173\u95ed\u804a\u5929")
            return self._fetch_live_chat_messages(live_chat_id, api_key, since_id)
        except YouTubeRequestError as exc:
            return DanmakuFetchResult.error_result(str(exc))

    def _check_video(self, video_id: str, api_key: str) -> LiveStatusResult:
        payload = self._request_json(
            self._VIDEOS_API,
            {
                "part": "snippet,liveStreamingDetails",
                "id": video_id,
                "key": api_key,
            },
        )
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return LiveStatusResult.unknown(f"video_id={video_id}, not found")

        item = items[0]
        snippet = item.get("snippet") if isinstance(item, dict) else {}
        details = item.get("liveStreamingDetails") if isinstance(item, dict) else {}
        title = str((snippet or {}).get("title") or "")
        live_state = str((snippet or {}).get("liveBroadcastContent") or "")
        started = str((details or {}).get("actualStartTime") or "")
        ended = str((details or {}).get("actualEndTime") or "")

        if live_state == "live" or (started and not ended):
            return LiveStatusResult.live(title=title, live_id=f"youtube:{video_id}:{started or 'live'}", detail=f"video_id={video_id}")
        return LiveStatusResult.offline(f"video_id={video_id}")

    def _check_channel(self, channel_id: str, api_key: str) -> LiveStatusResult:
        payload = self._request_json(
            self._SEARCH_API,
            {
                "part": "snippet",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": "1",
                "key": api_key,
            },
        )
        items = payload.get("items")
        if isinstance(items, list) and items:
            item = items[0]
            item_id = item.get("id") if isinstance(item, dict) else {}
            snippet = item.get("snippet") if isinstance(item, dict) else {}
            video_id = str((item_id or {}).get("videoId") or "")
            title = str((snippet or {}).get("title") or "")
            return LiveStatusResult.live(title=title, live_id=f"youtube:{video_id or channel_id}:live", detail=f"channel_id={channel_id}")
        return LiveStatusResult.offline(f"channel_id={channel_id}")

    def _resolve_live_chat_id(self, target: "YouTubeTarget", api_key: str) -> str:
        if target.video_id:
            return self._live_chat_id_from_video(target.video_id, api_key)
        if target.channel_id:
            video_id = self._live_video_id_from_channel(target.channel_id, api_key)
            if video_id:
                return self._live_chat_id_from_video(video_id, api_key)
        return ""

    def _live_video_id_from_channel(self, channel_id: str, api_key: str) -> str:
        payload = self._request_json(
            self._SEARCH_API,
            {
                "part": "snippet",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": "1",
                "key": api_key,
            },
        )
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return ""
        item = items[0]
        item_id = item.get("id") if isinstance(item, dict) else {}
        return str((item_id or {}).get("videoId") or "")

    def _live_chat_id_from_video(self, video_id: str, api_key: str) -> str:
        payload = self._request_json(
            self._VIDEOS_API,
            {
                "part": "liveStreamingDetails",
                "id": video_id,
                "key": api_key,
            },
        )
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return ""
        item = items[0]
        details = item.get("liveStreamingDetails") if isinstance(item, dict) else {}
        return str((details or {}).get("activeLiveChatId") or "")

    def _fetch_live_chat_messages(self, live_chat_id: str, api_key: str, page_token: str = "") -> DanmakuFetchResult:
        params = {
            "part": "snippet,authorDetails",
            "liveChatId": live_chat_id,
            "maxResults": "200",
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        payload = self._request_json(self._LIVE_CHAT_MESSAGES_API, params)
        messages = self._messages_from_live_chat_payload(payload)
        next_page_token = str(payload.get("nextPageToken") or "")
        detail = "" if messages else "\u6682\u65e0\u65b0\u804a\u5929"
        return DanmakuFetchResult.ok(messages, detail=detail, cursor=next_page_token)

    def _messages_from_live_chat_payload(self, payload: dict) -> list[DanmakuMessage]:
        items = payload.get("items")
        if not isinstance(items, list):
            return []

        messages: list[DanmakuMessage] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
            author_details = item.get("authorDetails") if isinstance(item.get("authorDetails"), dict) else {}
            content = self._message_text(snippet)
            if not content:
                continue
            author = str(author_details.get("displayName") or "").strip()
            sent_at = str(snippet.get("publishedAt") or "")
            message_id = str(item.get("id") or f"youtube:{sent_at}:{author}:{content}")
            messages.append(DanmakuMessage(author=author, content=content, sent_at=sent_at, message_id=message_id))
        return messages

    @staticmethod
    def _message_text(snippet: dict) -> str:
        display_message = snippet.get("displayMessage")
        if display_message:
            return str(display_message).strip()
        text_details = snippet.get("textMessageDetails")
        if isinstance(text_details, dict):
            return str(text_details.get("messageText") or "").strip()
        return ""

    def _request_json(self, url: str, params: dict[str, str]) -> dict:
        request = Request(f"{url}?{urlencode(params)}", headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise YouTubeRequestError(f"YouTube HTTP {exc.code}") from exc
        except URLError as exc:
            raise YouTubeRequestError(f"YouTube network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise YouTubeRequestError("YouTube request timeout") from exc
        except OSError as exc:
            raise YouTubeRequestError(f"YouTube request failed: {exc}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise YouTubeRequestError("YouTube response is not JSON") from exc
        if not isinstance(payload, dict):
            raise YouTubeRequestError("YouTube response is not an object")
        return payload

    @classmethod
    def extract_target(cls, value: str, remark: str = "") -> "YouTubeTarget":
        options = _parse_options(remark)
        if options.get("video_id") or options.get("channel_id"):
            return YouTubeTarget(video_id=options.get("video_id", ""), channel_id=options.get("channel_id", ""))

        value = value.strip()
        parsed = urlparse(value)
        query = parse_qs(parsed.query)
        video_id = query.get("v", [""])[0]
        if video_id:
            return YouTubeTarget(video_id=video_id)

        parts = [part for part in parsed.path.split("/") if part]
        if "youtu.be" in parsed.netloc and parts:
            return YouTubeTarget(video_id=parts[0])
        if parts and parts[0] in {"watch", "live"} and len(parts) > 1:
            return YouTubeTarget(video_id=parts[1])
        if parts and parts[0] == "channel" and len(parts) > 1:
            return YouTubeTarget(channel_id=parts[1])

        match = re.search(r"\b([A-Za-z0-9_-]{11})\b", value)
        if match:
            return YouTubeTarget(video_id=match.group(1))
        return YouTubeTarget()

    @staticmethod
    def _api_key(remark: str) -> str:
        options = _parse_options(remark)
        return options.get("api_key") or os.getenv("YOUTUBE_API_KEY", "")


class YouTubeTarget:
    def __init__(self, video_id: str = "", channel_id: str = "") -> None:
        self.video_id = video_id
        self.channel_id = channel_id


class YouTubeRequestError(Exception):
    pass


def _parse_options(remark: str) -> dict[str, str]:
    options: dict[str, str] = {}
    for line in remark.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            options[key] = value
    return options
