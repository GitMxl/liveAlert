from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from .models import AppSettings, ReminderRecord, StatusLogRecord, Streamer


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()
        self.settings = AppSettings()
        self.streamers: list[Streamer] = []
        self.history: list[ReminderRecord] = []
        self.status_logs: list[StatusLogRecord] = []
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._ensure_parent()
                self.save()
                return

            with self.path.open("r", encoding="utf-8") as file:
                raw = json.load(file)

            self.settings = AppSettings.from_dict(raw.get("settings"))
            self.streamers = [
                Streamer.from_dict(item)
                for item in raw.get("streamers", [])
                if isinstance(item, dict)
            ]
            self.history = [
                ReminderRecord.from_dict(item)
                for item in raw.get("history", [])
                if isinstance(item, dict)
            ]
            self.status_logs = [
                StatusLogRecord.from_dict(item)
                for item in raw.get("status_logs", [])
                if isinstance(item, dict)
            ]

    def save(self) -> None:
        with self._lock:
            self._ensure_parent()
            payload = {
                "settings": self.settings.to_dict(),
                "streamers": [streamer.to_dict() for streamer in self.streamers],
                "history": [record.to_dict() for record in self.history],
                "status_logs": [record.to_dict() for record in self.status_logs],
            }
            with self.path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)

    def list_streamers(self) -> list[Streamer]:
        with self._lock:
            return [Streamer.from_dict(item.to_dict()) for item in self.streamers]

    def get_settings(self) -> AppSettings:
        with self._lock:
            return AppSettings.from_dict(self.settings.to_dict())

    def update_settings(self, settings: AppSettings) -> None:
        with self._lock:
            self.settings = settings
            self.save()

    def add_streamer(self, streamer: Streamer) -> None:
        with self._lock:
            self.streamers.append(streamer)
            self.save()

    def update_streamer(self, streamer: Streamer) -> None:
        with self._lock:
            for index, current in enumerate(self.streamers):
                if current.id == streamer.id:
                    self.streamers[index] = streamer
                    self.save()
                    return
            raise KeyError(f"Streamer not found: {streamer.id}")

    def delete_streamer(self, streamer_id: str) -> None:
        with self._lock:
            self.streamers = [item for item in self.streamers if item.id != streamer_id]
            self.save()

    def replace_streamers(self, streamers: list[Streamer]) -> None:
        with self._lock:
            self.streamers = streamers
            self.save()

    def list_history(self, limit: int = 200) -> list[ReminderRecord]:
        with self._lock:
            records = [ReminderRecord.from_dict(item.to_dict()) for item in self.history]
            return records[-limit:]

    def add_history(self, record: ReminderRecord) -> None:
        with self._lock:
            self.history.append(record)
            self.history = self.history[-500:]
            self.save()

    def clear_history(self) -> None:
        with self._lock:
            self.history = []
            self.save()

    def list_status_logs(self, limit: int = 300) -> list[StatusLogRecord]:
        with self._lock:
            records = [StatusLogRecord.from_dict(item.to_dict()) for item in self.status_logs]
            return records[-limit:]

    def add_status_log(self, record: StatusLogRecord) -> None:
        with self._lock:
            self.status_logs.append(record)
            self.status_logs = self.status_logs[-1000:]
            self.save()

    def clear_status_logs(self) -> None:
        with self._lock:
            self.status_logs = []
            self.save()

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
