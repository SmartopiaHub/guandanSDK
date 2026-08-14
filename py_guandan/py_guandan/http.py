"""Central HTTP transport with safe loopback proxy handling."""

from __future__ import annotations

import socket
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter


def is_loopback_url(url: str) -> bool:
    """Return whether *url* targets localhost or a loopback IP address."""
    hostname = urlsplit(url).hostname or ""
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


class _TcpNoDelayAdapter(HTTPAdapter):
    """HTTP adapter that enables TCP_NODELAY on every pooled socket.

    The game server writes SSE events immediately, one small write per
    event. With Nagle enabled on the client side, the client's delayed
    ACKs let the server's kernel hold small writes until the *next*
    write flushes them — heartbeats arrive one period late, and the
    final event of a stream (e.g. ``test.completed``) is never flushed
    at all, leaving stream consumers such as the benchmark monitor
    hanging. TCP_NODELAY makes the client ACK immediately so the
    server's writes flush in real time.
    """

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "socket_options",
            [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)],
        )
        super().init_poolmanager(*args, **kwargs)


class HttpTransportError(RuntimeError):
    """Base error for network-level HTTP failures."""


class HttpTimeoutError(HttpTransportError):
    """Raised when an HTTP operation times out."""


class HttpConnectionError(HttpTransportError):
    """Raised when an HTTP connection cannot be established or is lost."""


class HttpResponseError(HttpTransportError):
    """Raised when an HTTP response has a non-success status."""

    def __init__(self, method: str, url: str, response: requests.Response) -> None:
        self.method = method.upper()
        self.url = url
        self.status_code = response.status_code
        self.response = response
        try:
            self.detail: Any = response.json()
        except ValueError:
            self.detail = response.text
        super().__init__(
            f"{self.method} {self.url} returned HTTP "
            f"{self.status_code}: {self.detail}"
        )


class GuandanHttpClient:
    """HTTP client that bypasses proxies for loopback destinations only."""

    def __init__(self) -> None:
        self._normal_session = requests.Session()
        self._direct_session = requests.Session()
        self._direct_session.trust_env = False
        nodelay_adapter = _TcpNoDelayAdapter()
        for session in (self._normal_session, self._direct_session):
            session.mount("http://", nodelay_adapter)
            session.mount("https://", nodelay_adapter)

    def session_for(self, url: str) -> requests.Session:
        return self._direct_session if is_loopback_url(url) else self._normal_session

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        try:
            return self.session_for(url).request(method, url, **kwargs)
        except requests.Timeout as error:
            raise HttpTimeoutError(str(error)) from error
        except requests.ConnectionError as error:
            raise HttpConnectionError(str(error)) from error
        except requests.RequestException as error:
            raise HttpTransportError(str(error)) from error

    def require_success(
        self,
        response: requests.Response,
        *,
        method: str,
        url: str,
    ) -> requests.Response:
        if not response.ok:
            raise HttpResponseError(method, url, response)
        return response

    def request_json(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if body is not None:
            kwargs["json"] = body
        response = self.request(method, url, **kwargs)
        self.require_success(response, method=method, url=url)
        if not response.content:
            return {"ok": True}
        try:
            data = response.json()
        except ValueError as error:
            raise HttpTransportError(
                f"{method.upper()} {url} returned invalid JSON"
            ) from error
        if not isinstance(data, dict):
            raise HttpTransportError(
                f"{method.upper()} {url} returned a non-object JSON response"
            )
        return data

    def close(self) -> None:
        self._normal_session.close()
        self._direct_session.close()


http_client = GuandanHttpClient()
