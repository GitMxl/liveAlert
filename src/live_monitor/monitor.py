from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Queue
from threading import Event, Lock, Thread
import time

from .adapters import AdapterRegistry
from .models import (
    STATUS_ERROR,
    STATUS_LIVE,
    STATUS_OFFLINE,
    DanmakuFetchResult,
    DanmakuMessage,
    LiveStatusResult,
    StatusLogRecord,
    Streamer,
    utc_now_iso,
)
from .storage import JsonStore


@dataclass(slots=True)
class MonitorEvent:
    kind: str
    streamer: Streamer | None = None
    message: str = ""
    danmaku_messages: list[DanmakuMessage] = field(default_factory=list)
    danmaku_cursor: str = ""


class MonitorService:
    def __init__(self, store: JsonStore, registry: AdapterRegistry) -> None:
        self.store = store
        self.registry = registry
        self.events: Queue[MonitorEvent] = Queue()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._checking = Event()
        self._danmaku_lock = Lock()
        self._danmaku_fetching: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._loop, name="live-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def check_once_async(self) -> None:
        Thread(target=self.check_once, name="manual-live-check", daemon=True).start()

    def check_streamer_async(self, streamer_id: str) -> None:
        Thread(target=self.check_streamer, args=(streamer_id,), name="selected-live-check", daemon=True).start()

    def fetch_danmaku_async(self, streamer_id: str, since_id: str = "") -> None:
        Thread(
            target=self.fetch_danmaku,
            args=(streamer_id, since_id),
            name="selected-danmaku-fetch",
            daemon=True,
        ).start()

    def fetch_danmaku(self, streamer_id: str, since_id: str = "") -> None:
        with self._danmaku_lock:
            if streamer_id in self._danmaku_fetching:
                self.events.put(MonitorEvent(kind="danmaku_busy", message="\u5f39\u5e55\u6b63\u5728\u83b7\u53d6\u4e2d"))
                return
            self._danmaku_fetching.add(streamer_id)

        try:
            streamer = self._find_streamer(streamer_id)
            if streamer is None:
                self.events.put(MonitorEvent(kind="danmaku_error", message="\u672a\u627e\u5230\u9009\u4e2d\u7684\u4e3b\u64ad"))
                return

            adapter = self.registry.get(streamer.platform)
            if adapter is None:
                result = DanmakuFetchResult.unsupported_result(f"\u672a\u627e\u5230\u5e73\u53f0\u9002\u914d\u5668\uff1a{streamer.platform}")
            else:
                try:
                    result = adapter.fetch_danmaku(self._streamer_with_platform_config(streamer), since_id=since_id)
                except Exception as exc:
                    result = DanmakuFetchResult.error_result(f"{type(exc).__name__}: {exc}")

            if result.error:
                self.events.put(MonitorEvent(kind="danmaku_error", streamer=streamer, message=result.error))
            elif result.unsupported:
                self.events.put(MonitorEvent(kind="danmaku_unsupported", streamer=streamer, message=result.detail))
            else:
                self.events.put(
                    MonitorEvent(
                        kind="danmaku_messages",
                        streamer=streamer,
                        message=result.detail,
                        danmaku_messages=result.messages,
                        danmaku_cursor=result.cursor,
                    )
                )
        finally:
            with self._danmaku_lock:
                self._danmaku_fetching.discard(streamer_id)

    def check_streamer(self, streamer_id: str) -> None:
        if self._checking.is_set():
            self.events.put(MonitorEvent(kind="info", message="\u4e0a\u4e00\u6b21\u68c0\u6d4b\u5c1a\u672a\u7ed3\u675f"))
            return

        self._checking.set()
        try:
            streamer = self._find_streamer(streamer_id)
            if streamer is None:
                self.events.put(MonitorEvent(kind="info", message="\u672a\u627e\u5230\u9009\u4e2d\u7684\u4e3b\u64ad"))
                return
            updated = self._check_streamer(streamer, ignore_backoff=True)
            self.store.update_streamer(updated)
            self.events.put(MonitorEvent(kind="streamer_updated", streamer=updated))
        finally:
            self._checking.clear()
            self.events.put(MonitorEvent(kind="check_finished", message=utc_now_iso()))

    def check_once(self) -> None:
        if self._checking.is_set():
            self.events.put(MonitorEvent(kind="info", message="\u4e0a\u4e00\u6b21\u68c0\u6d4b\u5c1a\u672a\u7ed3\u675f"))
            return

        self._checking.set()
        try:
            streamers = self.store.list_streamers()
            for streamer in streamers:
                if self._stop_event.is_set():
                    break
                if not streamer.enabled:
                    continue
                if self._is_before_custom_interval(streamer):
                    continue
                if self._is_in_backoff(streamer):
                    continue
                updated = self._check_streamer(streamer)
                self.store.update_streamer(updated)
                self.events.put(MonitorEvent(kind="streamer_updated", streamer=updated))
        finally:
            self._checking.clear()
            self.events.put(MonitorEvent(kind="check_finished", message=utc_now_iso()))

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.check_once()
            settings = self.store.get_settings()
            wait_seconds = max(10, settings.check_interval_seconds)
            self._stop_event.wait(wait_seconds)

    def _check_streamer(self, streamer: Streamer, ignore_backoff: bool = False) -> Streamer:
        adapter = self.registry.get(streamer.platform)
        previous_status = streamer.status
        previous_title = streamer.live_title

        if not ignore_backoff and self._is_in_backoff(streamer):
            return streamer

        if adapter is None:
            result = LiveStatusResult.error_result(f"\u672a\u627e\u5230\u5e73\u53f0\u9002\u914d\u5668\uff1a{streamer.platform}")
        else:
            try:
                result = adapter.check_live_status(self._streamer_with_platform_config(streamer))
            except Exception as exc:
                result = LiveStatusResult.error_result(f"{type(exc).__name__}: {exc}")

        streamer.status = result.status
        streamer.last_checked_at = result.checked_at
        streamer.last_error = result.error
        streamer.live_title = result.title or result.detail
        self._update_backoff(streamer, result)
        self._record_status_change(streamer, previous_status, result.status, previous_title, streamer.live_title)

        if result.status == STATUS_LIVE:
            if previous_status != STATUS_LIVE or not streamer.live_session_id:
                streamer.live_session_id = result.live_id or f"{streamer.id}:{int(time.time())}"
            elif result.live_id:
                streamer.live_session_id = result.live_id

            if self._should_notify(streamer):
                streamer.last_notified_session_id = streamer.live_session_id
                self.events.put(MonitorEvent(kind="live_started", streamer=streamer))
            elif self._should_notify_title_change(streamer, previous_status, previous_title):
                self.events.put(MonitorEvent(kind="title_changed", streamer=streamer, message=previous_title))
        elif result.status == STATUS_OFFLINE:
            streamer.live_session_id = ""
            streamer.live_title = ""

        return streamer

    def _should_notify(self, streamer: Streamer) -> bool:
        settings = self.store.get_settings()
        if not settings.notifications_enabled:
            return False
        if not streamer.remind_enabled:
            return False
        if not streamer.live_session_id:
            return False
        return streamer.last_notified_session_id != streamer.live_session_id

    def _should_notify_title_change(self, streamer: Streamer, previous_status: str, previous_title: str) -> bool:
        settings = self.store.get_settings()
        if not settings.notifications_enabled or not settings.title_change_notifications_enabled:
            return False
        if not streamer.remind_enabled:
            return False
        if previous_status != STATUS_LIVE or streamer.status != STATUS_LIVE:
            return False
        if not previous_title or not streamer.live_title:
            return False
        return previous_title != streamer.live_title

    def _find_streamer(self, streamer_id: str) -> Streamer | None:
        for streamer in self.store.list_streamers():
            if streamer.id == streamer_id:
                return streamer
        return None

    def _is_in_backoff(self, streamer: Streamer) -> bool:
        if not streamer.next_check_after:
            return False
        try:
            next_check = datetime.fromisoformat(streamer.next_check_after)
        except ValueError:
            return False
        return datetime.now(timezone.utc) < next_check

    def _is_before_custom_interval(self, streamer: Streamer) -> bool:
        if streamer.custom_interval_seconds <= 0 or not streamer.last_checked_at:
            return False
        try:
            last_checked = datetime.fromisoformat(streamer.last_checked_at)
        except ValueError:
            return False
        elapsed = datetime.now(timezone.utc).timestamp() - last_checked.timestamp()
        return elapsed < streamer.custom_interval_seconds

    def _update_backoff(self, streamer: Streamer, result: LiveStatusResult) -> None:
        settings = self.store.get_settings()
        if result.status != STATUS_ERROR:
            streamer.consecutive_failures = 0
            streamer.next_check_after = ""
            return

        streamer.consecutive_failures += 1
        if not settings.retry_backoff_enabled:
            streamer.next_check_after = ""
            return

        base = max(10, settings.check_interval_seconds)
        multiplier = 2 ** max(0, streamer.consecutive_failures - 1)
        delay = min(settings.max_backoff_seconds, base * multiplier)
        next_check = datetime.now(timezone.utc).timestamp() + delay
        streamer.next_check_after = datetime.fromtimestamp(next_check, timezone.utc).isoformat()

    def _record_status_change(
        self,
        streamer: Streamer,
        previous_status: str,
        current_status: str,
        previous_title: str,
        current_title: str,
    ) -> None:
        if previous_status != current_status:
            self.store.add_status_log(
                StatusLogRecord(
                    streamer_id=streamer.id,
                    nickname=streamer.nickname,
                    platform=streamer.platform,
                    room_url=streamer.room_url,
                    event_type="status_changed",
                    old_status=previous_status,
                    new_status=current_status,
                    old_title=previous_title,
                    new_title=current_title,
                    message=self._status_change_message(previous_status, current_status),
                )
            )
        elif previous_status == STATUS_LIVE and current_status == STATUS_LIVE and previous_title and current_title and previous_title != current_title:
            self.store.add_status_log(
                StatusLogRecord(
                    streamer_id=streamer.id,
                    nickname=streamer.nickname,
                    platform=streamer.platform,
                    room_url=streamer.room_url,
                    event_type="title_changed",
                    old_status=previous_status,
                    new_status=current_status,
                    old_title=previous_title,
                    new_title=current_title,
                    message="\u76f4\u64ad\u6807\u9898\u53d8\u5316",
                )
            )

    @staticmethod
    def _status_change_message(previous_status: str, current_status: str) -> str:
        if current_status == STATUS_LIVE:
            return "\u5f00\u64ad"
        if previous_status == STATUS_LIVE and current_status == STATUS_OFFLINE:
            return "\u4e0b\u64ad"
        if current_status == STATUS_ERROR:
            return "\u68c0\u6d4b\u5931\u8d25"
        if previous_status == STATUS_ERROR and current_status != STATUS_ERROR:
            return "\u68c0\u6d4b\u6062\u590d"
        return "\u72b6\u6001\u53d8\u5316"

    def _streamer_with_platform_config(self, streamer: Streamer) -> Streamer:
        settings = self.store.get_settings()
        config = settings.platform_configs.get(streamer.platform, {})
        if not config:
            return streamer
        cloned = Streamer.from_dict(streamer.to_dict())
        lines = [cloned.remark.strip()] if cloned.remark.strip() else []
        for key, value in config.items():
            if value:
                lines.append(f"{key}={value}")
        cloned.remark = "\n".join(lines)
        return cloned
