from .base import PlatformAdapter
from .bilibili import BilibiliAdapter
from .douyu import DouyuAdapter
from .generic_http import GenericHttpAdapter
from .huya import HuyaAdapter
from .mock import MockAdapter
from .placeholder import ReservedPlatformAdapter
from .registry import AdapterRegistry, create_default_registry
from .twitch import TwitchAdapter
from .youtube import YouTubeAdapter

__all__ = [
    "AdapterRegistry",
    "BilibiliAdapter",
    "DouyuAdapter",
    "GenericHttpAdapter",
    "HuyaAdapter",
    "MockAdapter",
    "PlatformAdapter",
    "ReservedPlatformAdapter",
    "TwitchAdapter",
    "YouTubeAdapter",
    "create_default_registry",
]
