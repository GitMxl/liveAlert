from __future__ import annotations

from live_monitor.adapters.base import PlatformAdapter
from live_monitor.adapters.bilibili import BilibiliAdapter
from live_monitor.adapters.douyu import DouyuAdapter
from live_monitor.adapters.generic_http import GenericHttpAdapter
from live_monitor.adapters.huya import HuyaAdapter
from live_monitor.adapters.mock import MockAdapter
from live_monitor.adapters.placeholder import ReservedPlatformAdapter
from live_monitor.adapters.twitch import TwitchAdapter
from live_monitor.adapters.youtube import YouTubeAdapter


class AdapterRegistry:
    def __init__(self, adapters: list[PlatformAdapter]) -> None:
        self._adapters = {adapter.name: adapter for adapter in adapters}

    def names(self) -> list[str]:
        return list(self._adapters.keys())

    def get(self, name: str) -> PlatformAdapter | None:
        return self._adapters.get(name)


def create_default_registry() -> AdapterRegistry:
    return AdapterRegistry(
        [
            MockAdapter(),
            GenericHttpAdapter(),
            BilibiliAdapter(),
            ReservedPlatformAdapter("\u6296\u97f3"),
            ReservedPlatformAdapter("\u5feb\u624b"),
            DouyuAdapter(),
            HuyaAdapter(),
            TwitchAdapter(),
            YouTubeAdapter(),
        ]
    )
