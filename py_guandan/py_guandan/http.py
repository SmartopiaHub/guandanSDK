"""Central HTTP transport with safe loopback proxy handling."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import requests


def is_loopback_url(url: str) -> bool:
    """Return whether *url* targets localhost or a loopback IP address."""
    hostname = urlsplit(url).hostname or ""
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


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
