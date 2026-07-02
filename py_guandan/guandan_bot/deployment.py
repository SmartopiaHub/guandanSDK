"""Client for programmatic bot deployment via the lobby developer API.

Authenticate with a unified developer API key (``sk-zq-*`` format) to manage
bot providers, definitions, and deployments without using the Flutter UI.

Usage::

    from guandan_bot.deployment import BotDeploymentClient

    client = BotDeploymentClient(
        lobby_url="https://www.zhiquguandan.com",
        api_key="sk-zq-...",
    )

    # Register a bot provider
    provider = client.create_provider(
        display_name="My Bot Provider",
        contact_email="bot@example.com",
    )

    # Create a bot definition
    definition = client.create_definition(
        provider_id=provider["provider"]["provider_id"],
        display_name="My Bot v1",
        version="1.0.0",
        bot_code="my_bot",
    )

    # Register a WebSocket deployment
    deployment = client.create_deployment(
        provider_id=provider["provider"]["provider_id"],
        transport_type="websocket",
        supported_bot_definition_ids=[definition["definition"]["bot_definition_id"]],
    )

    # For HTTP deployments, verify the base URL
    client.verify_deployment(
        deployment_id=deployment["deployment_id"],
        base_url="https://my-bot.example.com",
    )
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class BotDeploymentError(RuntimeError):
    """Raised when a bot deployment API call fails."""


@dataclass(frozen=True)
class BotDeploymentClient:
    """HTTP client for the lobby's programmatic bot-management API.

    Authenticates with a developer API key (``sk-zq-*`` format; legacy
    ``gdk_test_kid_*`` keys are also accepted during the deprecation window).
    """

    lobby_url: str
    api_key: str
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key must not be empty")

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def create_provider(
        self,
        display_name: str,
        contact_email: str,
    ) -> dict[str, Any]:
        """Register a new bot provider.

        Returns the full response including the ``provider`` object.
        """
        return self._post(
            "/api/v1/developer/bots/providers",
            {
                "display_name": display_name,
                "contact_email": contact_email,
            },
            scope="bots:manage",
        )

    def list_providers(self) -> dict[str, Any]:
        """List all bot providers, definitions, and deployments owned by the
        authenticated developer.

        Returns the same structure as ``GET /api/bots/mine``.
        """
        return self._get("/api/v1/developer/bots/providers", scope="bots:read")

    # ------------------------------------------------------------------
    # Definitions
    # ------------------------------------------------------------------

    def create_definition(
        self,
        provider_id: str,
        display_name: str,
        version: str,
        bot_code: str,
        *,
        description: str = "",
        supported_rule_sets: list[str] | None = None,
        supported_protocol_versions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new bot definition under the given provider."""
        if supported_rule_sets is None:
            supported_rule_sets = ["guandan-standard-v1"]
        if supported_protocol_versions is None:
            supported_protocol_versions = ["guandan-bot-v1"]
        return self._post(
            "/api/v1/developer/bots/definitions",
            {
                "provider_id": provider_id,
                "display_name": display_name,
                "version": version,
                "bot_code": bot_code,
                "description": description,
                "supported_rule_sets": supported_rule_sets,
                "supported_protocol_versions": supported_protocol_versions,
            },
            scope="bots:manage",
        )

    def list_definitions(self) -> dict[str, Any]:
        """Alias for ``list_providers`` (same endpoint returns everything)."""
        return self._get("/api/v1/developer/bots/definitions", scope="bots:read")

    # ------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------

    def create_deployment(
        self,
        provider_id: str,
        transport_type: str,
        supported_bot_definition_ids: list[str],
        *,
        supported_protocol_versions: list[str] | None = None,
        max_concurrent_sessions: int = 10,
        description: str = "",
    ) -> dict[str, Any]:
        """Register a new bot deployment.

        ``transport_type`` must be ``"websocket"`` or ``"http"``.

        Returns the full response including the one-time
        ``deployment_management_key`` and (for HTTP bots)
        ``bot_invocation_token``.
        """
        if supported_protocol_versions is None:
            supported_protocol_versions = ["guandan-bot-v1"]
        return self._post(
            "/api/v1/developer/bots/deployments",
            {
                "provider_id": provider_id,
                "transport_type": transport_type,
                "supported_bot_definition_ids": supported_bot_definition_ids,
                "supported_protocol_versions": supported_protocol_versions,
                "max_concurrent_sessions": max_concurrent_sessions,
                "description": description,
            },
            scope="bots:manage",
        )

    def delete_deployment(self, deployment_id: str) -> dict[str, Any]:
        """Delete a bot deployment."""
        return self._delete(
            f"/api/v1/developer/bots/deployments/{deployment_id}",
            scope="bots:manage",
        )

    def verify_deployment(
        self, deployment_id: str, base_url: str
    ) -> dict[str, Any]:
        """Verify the base URL of an HTTP bot deployment.

        The lobby server probes ``{base_url}/health`` to confirm the bot is
        reachable.
        """
        return self._post(
            f"/api/v1/developer/bots/deployments/{deployment_id}/verify",
            {"base_url": base_url},
            scope="bots:manage",
        )

    def deployment_health(self, deployment_id: str) -> dict[str, Any]:
        """Query the health status of a deployment."""
        return self._get(
            f"/api/v1/developer/bots/deployments/{deployment_id}/health",
            scope="bots:read",
        )

    def list_deployments(self) -> dict[str, Any]:
        """Alias for ``list_providers`` (same endpoint returns everything)."""
        return self._get("/api/v1/developer/bots/deployments", scope="bots:read")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, body: dict[str, Any], scope: str) -> dict[str, Any]:
        return self._request("POST", path, body, scope)

    def _get(self, path: str, scope: str) -> dict[str, Any]:
        return self._request("GET", path, None, scope)

    def _delete(self, path: str, scope: str) -> dict[str, Any]:
        return self._request("DELETE", path, None, scope)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        scope: str,
    ) -> dict[str, Any]:
        url = f"{self.lobby_url.rstrip('/')}{path}"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if method in ("POST",):
            headers["Idempotency-Key"] = str(uuid.uuid4())

        data = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=data, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                if method == "DELETE" and response.status == 204:
                    return {"deleted": True}
                return json.load(response)  # type: ignore[no-any-return]
        except HTTPError as exc:
            try:
                detail = json.load(exc)
            except Exception:
                detail = exc.read().decode(errors="replace")
            raise BotDeploymentError(
                f"{method} {path} failed: HTTP {exc.code}: {detail}"
            ) from exc
        except OSError as exc:
            raise BotDeploymentError(f"{method} {path} failed: {exc}") from exc
