#!/usr/bin/env python3
"""Deploy a bot to the Guandan platform via the developer API.

Reads an optional ``.env`` file from the current working directory to
resolve credentials and the lobby URL:

* ``BOT_DEPLOY_API_KEY`` — use this bot-management key directly.
* ``DEV_API_KEY`` — legacy fallback when no bot-specific key is configured.
* ``USERNAME`` / ``PASSWORD`` — log in with these credentials, then
  create a new developer API key.
* ``LOBBY_SERVER_URL`` — lobby server URL (default: ``http://localhost:8686``).

When no API key is found in ``.env``, a fresh key is created and the
user is offered to persist it to ``.env``.  The server only stores key
hashes, so existing keys cannot be retrieved.

If none of the above are found in ``.env``, the user is prompted
interactively.

Usage::

    python3 deploy_bot.py
"""

from __future__ import annotations

import argparse
import json
import os
import select
import sys
from datetime import datetime
from typing import Any

from guandan_bot.deployment import BotDeploymentClient, BotDeploymentError
from py_guandan.http import http_client


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------


class Colour:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREY = "\033[90m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


def log(title: str, summary: str = "", *, colour: str = Colour.BLUE) -> None:
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
    suffix = f" {Colour.DIM}{summary}{Colour.RESET}" if summary else ""
    print(
        f"{Colour.GREY}[{timestamp}]{Colour.RESET} "
        f"{colour}{Colour.BOLD}[{title}]{Colour.RESET}{suffix}",
        flush=True,
    )


def log_value(name: str, value: Any) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, indent=2)
    print(
        f"  {Colour.CYAN}{name}:{Colour.RESET} {Colour.MAGENTA}{value}{Colour.RESET}",
        flush=True,
    )


def step(number: int, title: str) -> None:
    print(
        f"\n{Colour.BOLD}{'━' * 8} Step {number}: {title} {'━' * 8}{Colour.RESET}",
        flush=True,
    )


def api_request(
    method: str,
    url: str,
    *,
    bearer: str = "",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if bearer:
        request_headers["Authorization"] = f"Bearer {bearer}"
    if headers:
        request_headers.update(headers)
    return http_client.request_json(
        method,
        url,
        body=body,
        headers=request_headers,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Timed input
# ---------------------------------------------------------------------------


def _timed_input(prompt: str, timeout: float) -> str | None:
    """Read a line from stdin with a timeout.  Returns *None* on timeout."""
    print(prompt, end="", flush=True)
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().strip()
    print()  # move past the prompt line after timeout
    return None


# ---------------------------------------------------------------------------
# .env file loading
# ---------------------------------------------------------------------------


def _load_dotenv(path: str | None = None) -> dict[str, str]:
    """Parse a ``.env`` file from the current working directory."""
    if path is None:
        path = os.path.join(os.getcwd(), ".env")
    elif not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)

    result: dict[str, str] = {}
    if not os.path.isfile(path):
        return result

    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            result[key] = value
    return result


# ---------------------------------------------------------------------------
# .env writing
# ---------------------------------------------------------------------------


def _write_to_dotenv(env_path: str, key: str, value: str) -> None:
    """Write or update a key-value pair in the ``.env`` file."""
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    else:
        lines = []

    updated = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            existing_key, _, _ = stripped.partition("=")
            if existing_key.strip() == key:
                lines[i] = f"{key}={value}\n"
                updated = True
                break

    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

_AUTO_DELETE_TIMEOUT = 10


def _prompt_api_key_workflow(
    lobby_url: str,
    access_token: str,
    env_path: str,
    *,
    replacing_incompatible_key: bool = False,
) -> tuple[str, str, bool]:
    """Prompt the user to create a new developer API key.

    Returns ``(api_key, key_id, should_delete)``.
    """
    print()
    if replacing_incompatible_key:
        print(
            f"  {Colour.YELLOW}The configured API key was found, but it does not"
            f" have the required bots:read and bots:manage scopes.{Colour.RESET}"
        )
        prompt = "  Create a bot-management API key? [Y/n]: "
    else:
        print(
            f"  {Colour.YELLOW}No bot-deployment API key found in .env."
            f"{Colour.RESET}"
        )
        prompt = "  Create a bot-management API key? [Y/n]: "
    answer = input(prompt).strip().lower()
    if answer not in ("", "y", "yes"):
        log("Aborted by user — no compatible API key available", colour=Colour.RED)
        sys.exit(1)

    key = api_request(
        "POST",
        f"{lobby_url}/api/v1/developer/keys",
        bearer=access_token,
        body={
            "name": (
                "BotDeploy"
                f" {datetime.now().astimezone().isoformat(timespec='seconds')}"
            ),
            "environment": "test",
            "scopes": ["bots:manage", "bots:read"],
        },
    )
    api_key_val: str = key["api_key"]
    key_id_val: str = key["key_id"]
    log("API key created", key_id_val, colour=Colour.GREEN)
    log_value("API key", api_key_val)

    # Offer to persist
    print()
    answer = input(
        f"  {Colour.YELLOW}Save API key to .env as BOT_DEPLOY_API_KEY?"
        f" [Y/n]{Colour.RESET} "
    ).strip().lower()
    if answer in ("", "y", "yes"):
        _write_to_dotenv(env_path, "BOT_DEPLOY_API_KEY", api_key_val)
        log("API key saved to .env", env_path, colour=Colour.GREEN)
        return api_key_val, key_id_val, False

    # Not saving — ask about deletion
    print()
    answer = _timed_input(
        f"  {Colour.YELLOW}Delete this key after deployment?"
        f" [Y/n]{Colour.RESET} "
        f"{Colour.DIM}(auto-delete in {_AUTO_DELETE_TIMEOUT} s){Colour.RESET}: ",
        _AUTO_DELETE_TIMEOUT,
    )
    should_delete = answer is None or answer.strip().lower() not in ("n", "no")
    if should_delete:
        log("Will auto-delete key after deployment", colour=Colour.DIM)
    else:
        log("Will keep key after deployment", key_id_val, colour=Colour.DIM)
    return api_key_val, key_id_val, should_delete


# ---------------------------------------------------------------------------
# Provider / definition helpers
# ---------------------------------------------------------------------------


def _print_providers(providers: list[dict[str, Any]]) -> None:
    print(f"\n  {Colour.BOLD}Existing providers:{Colour.RESET}")
    for i, p in enumerate(providers, 1):
        pid = p.get("provider_id", "?")
        name = p.get("display_name", "?")
        email = p.get("contact_email", "")
        print(
            f"  [{i}]  {Colour.CYAN}{pid}{Colour.RESET}"
            f"  {name}  {Colour.DIM}({email}){Colour.RESET}"
        )


def _print_definitions(definitions: list[dict[str, Any]]) -> None:
    print(f"\n  {Colour.BOLD}Existing bot definitions:{Colour.RESET}")
    for i, d in enumerate(definitions, 1):
        did = d.get("bot_definition_id", "?")
        name = d.get("display_name", "?")
        code = d.get("bot_code", "?")
        ver = d.get("version", "?")
        print(
            f"  [{i}]  {Colour.CYAN}{did}{Colour.RESET}"
            f"  {name}  {Colour.DIM}(bot_code={code}, v{ver}){Colour.RESET}"
        )


def _pick_or_create_provider(
    client: BotDeploymentClient,
) -> tuple[str, str]:
    """List existing providers and let the user pick one or create a new one.

    Returns ``(provider_id, provider_name)``.
    """
    try:
        data = client.list_providers()
    except BotDeploymentError:
        data = {}
    providers: list[dict[str, Any]] = data.get("providers", []) or []

    if providers:
        _print_providers(providers)
        print(
            f"\n  {Colour.DIM}Enter 1-{len(providers)} to select,"
            f" or 'n' to create a new provider:{Colour.RESET}"
        )
        choice = input("  > ").strip()
        if choice.lower() not in ("n", "new"):
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(providers):
                    p = providers[idx]
                    pid: str = p["provider_id"]
                    name: str = p.get("display_name", pid)
                    log("Using provider", f"{name} ({pid})", colour=Colour.GREEN)
                    return pid, name
            except ValueError:
                pass

    # Create new provider
    print()
    log("Create new provider", colour=Colour.BLUE)
    display_name = input("  Provider display name: ").strip()
    if not display_name:
        log("Provider name required", colour=Colour.RED)
        sys.exit(1)
    contact_email = input("  Contact email: ").strip()
    if not contact_email:
        log("Contact email required", colour=Colour.RED)
        sys.exit(1)

    try:
        result = client.create_provider(display_name, contact_email)
    except BotDeploymentError as exc:
        log("Failed to create provider", str(exc), colour=Colour.RED)
        sys.exit(1)

    provider = result["provider"]
    pid = provider["provider_id"]
    log("Provider created", f"{display_name} ({pid})", colour=Colour.GREEN)
    return pid, display_name


def _pick_or_create_definition(
    client: BotDeploymentClient,
    provider_id: str,
    *,
    parameters: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """List definitions for the provider and let the user pick or create.

    ``parameters`` (an optional typed-parameter schema) is passed to
    ``create_definition`` when a new definition is created.

    Returns ``(bot_definition_id, bot_code)``.
    """
    try:
        data = client.list_definitions()
    except BotDeploymentError:
        data = {}
    all_defs: list[dict[str, Any]] = data.get("bot_definitions", []) or []
    defs = [
        d for d in all_defs
        if d.get("provider_id") == provider_id
    ]

    if defs:
        _print_definitions(defs)
        print(
            f"\n  {Colour.DIM}Enter 1-{len(defs)} to select,"
            f" or 'n' to create a new definition:{Colour.RESET}"
        )
        choice = input("  > ").strip()
        if choice.lower() not in ("n", "new"):
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(defs):
                    d = defs[idx]
                    did: str = d["bot_definition_id"]
                    code: str = d.get("bot_code", did)
                    log(
                        "Using definition",
                        f"{d.get('display_name', '?')} ({did})",
                        colour=Colour.GREEN,
                    )
                    return did, code
            except ValueError:
                pass

    # Create new definition
    print()
    log("Create new bot definition", colour=Colour.BLUE)
    display_name = input("  Bot display name: ").strip()
    if not display_name:
        log("Bot display name required", colour=Colour.RED)
        sys.exit(1)
    bot_code = input("  Bot code (unique identifier): ").strip()
    if not bot_code:
        log("Bot code required", colour=Colour.RED)
        sys.exit(1)
    version = input("  Version [1.0.0]: ").strip() or "1.0.0"

    try:
        result = client.create_definition(
            provider_id=provider_id,
            display_name=display_name,
            version=version,
            bot_code=bot_code,
            parameters=parameters,
        )
    except BotDeploymentError as exc:
        log("Failed to create definition", str(exc), colour=Colour.RED)
        sys.exit(1)

    definition = result["definition"]
    did = definition["bot_definition_id"]
    log("Definition created", f"{display_name} ({did})", colour=Colour.GREEN)
    return did, bot_code


# ---------------------------------------------------------------------------
# Deployment creation
# ---------------------------------------------------------------------------


def _display_deployment_info(result: dict[str, Any]) -> None:
    """Print the deployment details after a successful creation."""
    dep = result.get("deployment", {})
    print()
    print(f"{Colour.BOLD}{'─' * 60}{Colour.RESET}")
    print(
        f"  {Colour.GREEN}{Colour.BOLD}Deployment created successfully!{Colour.RESET}"
    )
    print(f"{Colour.BOLD}{'─' * 60}{Colour.RESET}")
    log_value("Deployment ID", dep.get("deployment_id", "?"))
    log_value("Transport type", dep.get("transport_type", "?"))
    log_value("Status", dep.get("status", "?"))
    if dep.get("base_url"):
        log_value("Base URL", dep["base_url"])
    log_value("Max concurrent sessions", dep.get("max_concurrent_sessions", "?"))
    log_value(
        "Bot definition IDs", dep.get("supported_bot_definition_ids", [])
    )

    # These are only returned once — highlight them
    mgmt_key = result.get("deployment_management_key", "")
    if mgmt_key:
        print()
        log_value(
            f"{Colour.YELLOW}Deployment management key{Colour.RESET}",
            mgmt_key,
        )
        print(
            f"  {Colour.YELLOW}⚠  Store this key securely."
            f" It is only shown once!{Colour.RESET}"
        )

    invocation_token = result.get("bot_invocation_token", "")
    if invocation_token:
        print()
        log_value(
            f"{Colour.YELLOW}Bot invocation token (HTTP only){Colour.RESET}",
            invocation_token,
        )
        print(
            f"  {Colour.YELLOW}⚠  Store this token securely."
            f" It is only shown once!{Colour.RESET}"
        )

    api_key_val = result.get("api_key", "")
    if api_key_val and api_key_val != mgmt_key:
        log_value("API key", api_key_val)

    print(f"{Colour.BOLD}{'─' * 60}{Colour.RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy a bot to the Guandan lobby.",
    )
    parser.add_argument(
        "--parameters",
        help=(
            "JSON typed-parameter schema for a newly created definition, "
            "e.g. '[{\"name\": \"strength\", \"type\": \"integer\", "
            "\"default\": 50, \"min\": 0}]'"
        ),
    )
    parser.add_argument(
        "--parameter-values",
        help=(
            "JSON deployment-time parameter values, "
            "e.g. '{\"strength\": 25}'"
        ),
    )
    args = parser.parse_args()
    parameters: list[dict[str, Any]] | None = None
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError:
            log("--parameters must be valid JSON", colour=Colour.RED)
            return 1
    parameter_values: dict[str, Any] | None = None
    if args.parameter_values:
        try:
            parameter_values = json.loads(args.parameter_values)
        except json.JSONDecodeError:
            log("--parameter-values must be valid JSON", colour=Colour.RED)
            return 1

    print(
        f"{Colour.BOLD}Guandan Bot Deployment{Colour.RESET}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Load .env from the current working directory
    # ------------------------------------------------------------------
    env = _load_dotenv()
    env_path = os.path.join(os.getcwd(), ".env")

    # ------------------------------------------------------------------
    # Resolve lobby URL
    # ------------------------------------------------------------------
    lobby_url = env.get("LOBBY_SERVER_URL", "").strip()
    if not lobby_url:
        lobby_url = (
            input("Lobby server URL [http://localhost:8686]: ").strip()
            or "http://localhost:8686"
        )
    lobby_url = lobby_url.rstrip("/")

    # ------------------------------------------------------------------
    # Resolve credentials
    # ------------------------------------------------------------------
    bot_deploy_api_key = env.get("BOT_DEPLOY_API_KEY", "").strip()
    dev_api_key = env.get("DEV_API_KEY", "").strip()
    env_username = env.get("USERNAME", "").strip()
    env_password = env.get("PASSWORD", "").strip()

    access_token = ""
    api_key = ""
    key_id = ""
    should_delete_key = False

    configured_api_key = bot_deploy_api_key or dev_api_key
    if configured_api_key:
        api_key = configured_api_key
        key_name = "BOT_DEPLOY_API_KEY" if bot_deploy_api_key else "DEV_API_KEY"
        log(f"Using {key_name} from .env", colour=Colour.GREEN)
    else:
        # ── Log in and create API key ──
        step(1, "Log in")
        username = env_username or input("Username: ").strip()
        password = env_password or input("Password: ").strip()
        if not username or not password:
            log("Credentials required", colour=Colour.RED)
            return 1
        login = api_request(
            "POST",
            f"{lobby_url}/api/auth/login",
            body={"account": username, "password": password},
        )
        access_token = login["tokens"]["accessToken"]["token"]
        log("Logged in", login["user"]["id"], colour=Colour.GREEN)

        step(2, "Developer API key")
        api_key, key_id, should_delete_key = _prompt_api_key_workflow(
            lobby_url, access_token, env_path
        )

    # ------------------------------------------------------------------
    # Build the deployment client
    # ------------------------------------------------------------------
    try:
        client = BotDeploymentClient(lobby_url=lobby_url, api_key=api_key)
    except ValueError as exc:
        log("Invalid client config", str(exc), colour=Colour.RED)
        return 1

    if configured_api_key:
        try:
            client.list_providers()
        except BotDeploymentError as exc:
            log(
                "Configured API key cannot manage bots",
                str(exc),
                colour=Colour.YELLOW,
            )
            if not env_username or not env_password:
                log(
                    "Bot-management credentials required",
                    "Set USERNAME and PASSWORD, or BOT_DEPLOY_API_KEY with "
                    "bots:read and bots:manage scopes.",
                    colour=Colour.RED,
                )
                return 1

            step(1, "Log in")
            login = api_request(
                "POST",
                f"{lobby_url}/api/auth/login",
                body={"account": env_username, "password": env_password},
            )
            access_token = login["tokens"]["accessToken"]["token"]
            log("Logged in", login["user"]["id"], colour=Colour.GREEN)

            step(2, "Developer API key")
            api_key, key_id, should_delete_key = _prompt_api_key_workflow(
                lobby_url,
                access_token,
                env_path,
                replacing_incompatible_key=True,
            )
            client = BotDeploymentClient(lobby_url=lobby_url, api_key=api_key)

    try:
        # ------------------------------------------------------------------
        # Pick or create provider
        # ------------------------------------------------------------------
        step(3, "Bot provider")
        provider_id, provider_name = _pick_or_create_provider(client)

        # ------------------------------------------------------------------
        # Pick or create definition
        # ------------------------------------------------------------------
        step(4, "Bot definition")
        bot_definition_id, bot_code = _pick_or_create_definition(
            client, provider_id, parameters=parameters
        )

        # ------------------------------------------------------------------
        # Prompt for transport type and deployment details
        # ------------------------------------------------------------------
        step(5, "Deployment details")
        print()
        print(f"  {Colour.BOLD}Transport type:{Colour.RESET}")
        print(f"  [1] HTTP  — the lobby sends HTTP requests to your bot")
        print(f"  [2] WebSocket — your bot connects to a game server")
        while True:
            transport_choice = input("  Choose [1/2]: ").strip()
            if transport_choice == "1":
                transport_type = "http"
                break
            elif transport_choice == "2":
                transport_type = "websocket"
                break
            print(f"  {Colour.RED}Enter 1 or 2.{Colour.RESET}")

        base_url = ""
        if transport_type == "http":
            print()
            base_url = input(
                f"  Base URL {Colour.DIM}(e.g. https://my-bot.example.com){Colour.RESET}: "
            ).strip()
            if not base_url:
                log("Base URL is required for HTTP deployments", colour=Colour.RED)
                return 1

        print()
        max_sessions_str = input(
            f"  Max concurrent sessions {Colour.DIM}[10]{Colour.RESET}: "
        ).strip()
        try:
            max_concurrent_sessions = (
                int(max_sessions_str) if max_sessions_str else 10
            )
        except ValueError:
            log("Invalid number, using default 10", colour=Colour.YELLOW)
            max_concurrent_sessions = 10

        # ------------------------------------------------------------------
        # Create the deployment
        # ------------------------------------------------------------------
        step(6, "Create deployment")
        log(
            "Deploying",
            f"type={transport_type}, provider={provider_name},"
            f" bot={bot_code}",
        )

        try:
            result = client.create_deployment(
                provider_id=provider_id,
                transport_type=transport_type,
                supported_bot_definition_ids=[bot_definition_id],
                max_concurrent_sessions=max_concurrent_sessions,
                parameter_values=parameter_values,
            )
        except BotDeploymentError as exc:
            log("Deployment failed", str(exc), colour=Colour.RED)
            print()
            print(
                f"  {Colour.RED}The server rejected the deployment request.{Colour.RESET}"
            )
            print(f"  {Colour.DIM}Check that:{Colour.RESET}")
            print(
                f"  {Colour.DIM}  • The API key has 'bots:manage' scope{Colour.RESET}"
            )
            print(
                f"  {Colour.DIM}  • The provider exists and is active{Colour.RESET}"
            )
            print(
                f"  {Colour.DIM}  • The bot definition belongs to the provider{Colour.RESET}"
            )
            print(
                f"  {Colour.DIM}  • The transport type and base URL are valid{Colour.RESET}"
            )
            return 1

        _display_deployment_info(result)

        # If HTTP, offer to verify
        if transport_type == "http" and base_url:
            step(7, "Verify deployment")
            log("Verifying base URL", base_url)
            try:
                verify_result = client.verify_deployment(
                    deployment_id=result["deployment"]["deployment_id"],
                    base_url=base_url,
                )
                log(
                    "Verification result",
                    json.dumps(verify_result, ensure_ascii=False, indent=2),
                    colour=Colour.GREEN,
                )
            except BotDeploymentError as exc:
                log("Verification failed", str(exc), colour=Colour.YELLOW)
                print(
                    f"  {Colour.YELLOW}The deployment was created but"
                    f" verification failed.{Colour.RESET}"
                )
                print(
                    f"  {Colour.DIM}You can verify manually later.{Colour.RESET}"
                )

        return 0

    except (EOFError, KeyboardInterrupt):
        log("Interrupted", "cleaning up", colour=Colour.YELLOW)
        return 130
    except Exception as error:
        log("Deployment failed", str(error), colour=Colour.RED)
        return 1
    finally:
        if key_id and access_token and should_delete_key:
            try:
                api_request(
                    "DELETE",
                    f"{lobby_url}/api/v1/developer/keys/{key_id}",
                    bearer=access_token,
                )
                log("API key deleted", key_id, colour=Colour.GREEN)
            except Exception as error:
                log("API-key cleanup warning", str(error), colour=Colour.YELLOW)
        elif key_id and not should_delete_key:
            log("API key kept", key_id, colour=Colour.DIM)


if __name__ == "__main__":
    sys.exit(main())
