from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


STATUS_UNKNOWN = "unknown"
STATUS_OFFLINE = "offline"
STATUS_LIVE = "live"
STATUS_ERROR = "error"

STATUS_LABELS = {
    STATUS_UNKNOWN: "\u672a\u77e5",
    STATUS_OFFLINE: "\u672a\u5f00\u64ad",
    STATUS_LIVE: "\u76f4\u64ad\u4e2d",
    STATUS_ERROR: "\u68c0\u6d4b\u5931\u8d25",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid4().hex


@dataclass(slots=True)
class Streamer:
    nickname: str
    platform: str
    room_url: str
    remark: str = ""
    group: str = ""
    favorite: bool = False
    enabled: bool = True
    remind_enabled: bool = True
    id: str = field(default_factory=new_id)
    avatar_url: str = ""
    status: str = STATUS_UNKNOWN
    last_checked_at: str = ""
    last_error: str = ""
    live_title: str = ""
    live_session_id: str = ""
    last_notified_session_id: str = ""
    consecutive_failures: int = 0
    next_check_after: str = ""
    custom_interval_seconds: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Streamer":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        values = {key: data[key] for key in data if key in allowed}
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppSettings:
    check_interval_seconds: int = 60
    notifications_enabled: bool = True
    sound_enabled: bool = True
    retry_backoff_enabled: bool = True
    max_backoff_seconds: int = 900
    title_change_notifications_enabled: bool = True
    platform_configs: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AppSettings":
        if not data:
            return cls()
        settings = cls()
        interval = data.get("check_interval_seconds", settings.check_interval_seconds)
        try:
            settings.check_interval_seconds = max(10, int(interval))
        except (TypeError, ValueError):
            settings.check_interval_seconds = 60
        settings.notifications_enabled = bool(data.get("notifications_enabled", True))
        settings.sound_enabled = bool(data.get("sound_enabled", True))
        settings.retry_backoff_enabled = bool(data.get("retry_backoff_enabled", True))
        settings.title_change_notifications_enabled = bool(data.get("title_change_notifications_enabled", True))
        max_backoff = data.get("max_backoff_seconds", settings.max_backoff_seconds)
        try:
            settings.max_backoff_seconds = max(60, int(max_backoff))
        except (TypeError, ValueError):
            settings.max_backoff_seconds = 900
        configs = data.get("platform_configs", {})
        if isinstance(configs, dict):
            settings.platform_configs = {
                str(platform): {str(key): str(value) for key, value in values.items() if value is not None}
                for platform, values in configs.items()
                if isinstance(values, dict)
            }
        return settings

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReminderRecord:
    streamer_id: str
    nickname: str
    platform: str
    room_url: str
    title: str = ""
    live_session_id: str = ""
    notified_at: str = field(default_factory=utc_now_iso)
    id: str = field(default_factory=new_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReminderRecord":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        values = {key: data[key] for key in data if key in allowed}
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StatusLogRecord:
    streamer_id: str
    nickname: str
    platform: str
    room_url: str
    event_type: str
    old_status: str = ""
    new_status: str = ""
    old_title: str = ""
    new_title: str = ""
    message: str = ""
    logged_at: str = field(default_factory=utc_now_iso)
    id: str = field(default_factory=new_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StatusLogRecord":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        values = {key: data[key] for key in data if key in allowed}
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DanmakuMessage:
    content: str
    author: str = ""
    sent_at: str = field(default_factory=utc_now_iso)
    message_id: str = field(default_factory=new_id)


@dataclass(slots=True)
class DanmakuFetchResult:
    messages: list[DanmakuMessage] = field(default_factory=list)
    detail: str = ""
    error: str = ""
    unsupported: bool = False
    cursor: str = ""

    @classmethod
    def ok(cls, messages: list[DanmakuMessage], detail: str = "", cursor: str = "") -> "DanmakuFetchResult":
        return cls(messages=messages, detail=detail, cursor=cursor)

    @classmethod
    def unsupported_result(cls, detail: str) -> "DanmakuFetchResult":
        return cls(detail=detail, unsupported=True)

    @classmethod
    def error_result(cls, error: str) -> "DanmakuFetchResult":
        return cls(error=error)


@dataclass(slots=True)
class LiveStatusResult:
    status: str
    checked_at: str = field(default_factory=utc_now_iso)
    title: str = ""
    live_id: str = ""
    detail: str = ""
    error: str = ""

    @classmethod
    def live(cls, title: str = "", live_id: str = "", detail: str = "") -> "LiveStatusResult":
        return cls(status=STATUS_LIVE, title=title, live_id=live_id, detail=detail)

    @classmethod
    def offline(cls, detail: str = "") -> "LiveStatusResult":
        return cls(status=STATUS_OFFLINE, detail=detail)

    @classmethod
    def unknown(cls, detail: str = "") -> "LiveStatusResult":
        return cls(status=STATUS_UNKNOWN, detail=detail)

    @classmethod
    def error_result(cls, error: str) -> "LiveStatusResult":
        return cls(status=STATUS_ERROR, error=error)
