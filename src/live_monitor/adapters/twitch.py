from __future__ import annotations

import json
import os
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.models import DanmakuFetchResult, DanmakuMessage, LiveStatusResult, Streamer


class TwitchAdapter(PlatformAdapter):
    name = "Twitch"
    display_name = "Twitch"

    _STREAMS_API = "https://api.twitch.tv/helix/streams"
    _WATCH_URL = "https://www.twitch.tv/{channel}"
    _IRC_HOST = "irc.chat.twitch.tv"
    _IRC_PORT = 6697

    def check_live_status(self, streamer: Streamer) -> LiveStatusResult:
        channel = self.extract_channel(streamer.room_url)
        if not channel:
            return LiveStatusResult.error_result("Twitch needs a channel name or URL")

        credentials = self._credentials(streamer.remark)
        if not credentials:
            return LiveStatusResult.unknown(
                "Twitch official API requires TWITCH_CLIENT_ID and TWITCH_APP_TOKEN, or remark client_id/app_token"
            )

        client_id, app_token = credentials
        try:
            payload = self._request_json(channel, client_id, app_token)
        except TwitchRequestError as exc:
            return LiveStatusResult.error_result(str(exc))

        items = payload.get("data")
        if isinstance(items, list) and items:
            item = items[0]
            title = str(item.get("title") or "")
            stream_id = str(item.get("id") or channel)
            started_at = str(item.get("started_at") or "")
            return LiveStatusResult.live(title=title, live_id=f"twitch:{stream_id}:{started_at}", detail=f"channel={channel}")
        return LiveStatusResult.offline(f"channel={channel}")

    def build_watch_url(self, streamer: Streamer) -> str:
        channel = self.extract_channel(streamer.room_url)
        if channel:
            return self._WATCH_URL.format(channel=channel)
        return streamer.room_url

    def fetch_danmaku(self, streamer: Streamer, since_id: str = "") -> DanmakuFetchResult:
        channel = self.extract_channel(streamer.room_url)
        if not channel:
            return DanmakuFetchResult.error_result("Twitch needs a channel name or URL")

        credentials = self._chat_credentials(streamer.remark)
        if not credentials:
            return DanmakuFetchResult.unsupported_result(
                "Twitch \u804a\u5929\u9700\u8981\u914d\u7f6e chat_oauth \u548c chat_nick\uff0cOAuth token \u9700\u5177\u5907 chat:read"
            )

        token, nick = credentials
        listen_seconds = self._chat_listen_seconds(streamer.remark)
        try:
            messages = self._read_irc_messages(channel, nick, token, listen_seconds)
        except TwitchRequestError as exc:
            return DanmakuFetchResult.error_result(str(exc))

        messages = self._messages_after(messages, since_id)
        detail = "" if messages else "\u6682\u65e0\u65b0\u804a\u5929"
        return DanmakuFetchResult.ok(messages, detail=detail)

    @classmethod
    def extract_channel(cls, value: str) -> str:
        value = value.strip()
        if value and "/" not in value and "?" not in value and not value.startswith(("http://", "https://")):
            return value.lstrip("@")

        parsed = urlparse(value)
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            return parts[0].lstrip("@")

        match = re.search(r"twitch\.tv/([^/?#]+)", value)
        return match.group(1).lstrip("@") if match else ""

    def _request_json(self, channel: str, client_id: str, app_token: str) -> dict:
        url = f"{self._STREAMS_API}?{urlencode({'user_login': channel})}"
        request = Request(
            url,
            headers={
                "Client-ID": client_id,
                "Authorization": f"Bearer {app_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read(1024 * 1024).decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise TwitchRequestError(f"Twitch HTTP {exc.code}") from exc
        except URLError as exc:
            raise TwitchRequestError(f"Twitch network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TwitchRequestError("Twitch request timeout") from exc
        except OSError as exc:
            raise TwitchRequestError(f"Twitch request failed: {exc}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise TwitchRequestError("Twitch response is not JSON") from exc
        if not isinstance(payload, dict):
            raise TwitchRequestError("Twitch response is not an object")
        return payload

    @staticmethod
    def _credentials(remark: str) -> tuple[str, str] | None:
        options = _parse_options(remark)
        client_id = options.get("client_id") or os.getenv("TWITCH_CLIENT_ID", "")
        app_token = options.get("app_token") or options.get("token") or os.getenv("TWITCH_APP_TOKEN", "")
        if client_id and app_token:
            return client_id, app_token
        return None

    def _read_irc_messages(self, channel: str, nick: str, token: str, listen_seconds: int) -> list[DanmakuMessage]:
        token = token if token.startswith("oauth:") else f"oauth:{token}"
        messages: list[DanmakuMessage] = []
        raw_buffer = ""
        deadline = time.time() + listen_seconds

        try:
            with socket.create_connection((self._IRC_HOST, self._IRC_PORT), timeout=8) as base_socket:
                context = ssl.create_default_context()
                with context.wrap_socket(base_socket, server_hostname=self._IRC_HOST) as irc_socket:
                    irc_socket.settimeout(0.5)
                    self._send_irc(
                        irc_socket,
                        [
                            "CAP REQ :twitch.tv/tags twitch.tv/commands",
                            f"PASS {token}",
                            f"NICK {nick}",
                            f"JOIN #{channel.lower()}",
                        ],
                    )

                    while time.time() < deadline and len(messages) < 50:
                        try:
                            chunk = irc_socket.recv(4096)
                        except socket.timeout:
                            continue
                        if not chunk:
                            break
                        raw_buffer += chunk.decode("utf-8", errors="replace")
                        while "\r\n" in raw_buffer:
                            line, raw_buffer = raw_buffer.split("\r\n", 1)
                            if line.startswith("PING "):
                                self._send_irc(irc_socket, [line.replace("PING", "PONG", 1)])
                                continue
                            parsed = self._parse_privmsg(line)
                            if parsed:
                                messages.append(parsed)
        except OSError as exc:
            raise TwitchRequestError(f"Twitch IRC connection failed: {exc}") from exc

        return messages

    @staticmethod
    def _send_irc(irc_socket: ssl.SSLSocket, lines: list[str]) -> None:
        payload = "".join(f"{line}\r\n" for line in lines)
        irc_socket.sendall(payload.encode("utf-8"))

    @classmethod
    def _parse_privmsg(cls, line: str) -> DanmakuMessage | None:
        if " PRIVMSG " not in line:
            return None

        tags: dict[str, str] = {}
        rest = line
        if rest.startswith("@"):
            raw_tags, _, rest = rest.partition(" ")
            tags = cls._parse_irc_tags(raw_tags[1:])

        message_marker = " :"
        if message_marker not in rest:
            return None
        prefix_and_command, content = rest.rsplit(message_marker, 1)
        if " PRIVMSG " not in prefix_and_command:
            return None

        author = tags.get("display-name") or cls._author_from_prefix(prefix_and_command)
        message_id = tags.get("id") or f"twitch:{tags.get('tmi-sent-ts', '')}:{author}:{content}"
        sent_at = cls._sent_at_from_tag(tags.get("tmi-sent-ts", ""))
        return DanmakuMessage(author=author, content=content, sent_at=sent_at, message_id=message_id)

    @staticmethod
    def _parse_irc_tags(raw_tags: str) -> dict[str, str]:
        tags: dict[str, str] = {}
        for item in raw_tags.split(";"):
            key, _, value = item.partition("=")
            if key:
                tags[key] = _unescape_irc_tag(value)
        return tags

    @staticmethod
    def _author_from_prefix(value: str) -> str:
        match = re.search(r":([^! ]+)!", value)
        return match.group(1) if match else ""

    @staticmethod
    def _sent_at_from_tag(value: str) -> str:
        if not value:
            return ""
        try:
            timestamp = int(value) / 1000
        except ValueError:
            return ""
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

    @staticmethod
    def _chat_credentials(remark: str) -> tuple[str, str] | None:
        options = _parse_options(remark)
        token = (
            options.get("chat_oauth")
            or options.get("chat_token")
            or options.get("oauth")
            or os.getenv("TWITCH_CHAT_OAUTH", "")
            or os.getenv("TWITCH_CHAT_TOKEN", "")
        )
        nick = options.get("chat_nick") or options.get("nick") or os.getenv("TWITCH_CHAT_NICK", "")
        if token and nick:
            return token, nick
        return None

    @staticmethod
    def _chat_listen_seconds(remark: str) -> int:
        options = _parse_options(remark)
        try:
            return min(10, max(2, int(options.get("chat_listen_seconds", "4"))))
        except ValueError:
            return 4

    @staticmethod
    def _messages_after(messages: list[DanmakuMessage], since_id: str) -> list[DanmakuMessage]:
        if not since_id:
            return messages[-50:]
        for index, message in enumerate(messages):
            if message.message_id == since_id:
                return messages[index + 1 :][-50:]
        return messages[-50:]


class TwitchRequestError(Exception):
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


def _unescape_irc_tag(value: str) -> str:
    return (
        value.replace(r"\s", " ")
        .replace(r"\:", ";")
        .replace(r"\r", "\r")
        .replace(r"\n", "\n")
        .replace(r"\\", "\\")
    )
