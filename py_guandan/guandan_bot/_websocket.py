"""Shared compatibility helpers for WebSocket transports."""

from __future__ import annotations

import inspect
import ipaddress
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit


def loopback_proxy_options(connect: Callable[..., Any], uri: str) -> dict[str, Any]:
    """Disable automatic proxies for loopback URLs when supported.

    ``websockets`` added automatic proxy discovery and the ``proxy`` argument
    in version 15. Older versions forward unknown keywords to the event loop,
    so the option must only be supplied when it appears explicitly.
    """

    if "proxy" not in inspect.signature(connect).parameters:
        return {}

    hostname = urlsplit(uri).hostname
    if hostname is None:
        return {}
    if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
        return {"proxy": None}
    try:
        if ipaddress.ip_address(hostname).is_loopback:
            return {"proxy": None}
    except ValueError:
        pass
    return {}
