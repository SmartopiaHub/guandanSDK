"""End-to-end test: a script benchmark run lands in the UI-visible history.

Runs the real ``python -m guandan_benchmark`` command (builtin bots, 2
rounds) against a live lobby, then verifies via the session-authenticated
``GET /api/benchmarks`` endpoint that a completed history row exists with
the expected name and ``rounds_completed == 2``.

Requires a lobby server and at least one registered game server to be
running (guandan-test server-lifecycle conventions).  The test is skipped
when the lobby is unreachable.  Credentials default to the local lobby's
bootstrap site admin; override with environment variables:

    GUANDAN_E2E_LOBBY_URL       (default http://127.0.0.1:8686)
    GUANDAN_E2E_ADMIN_PASSWORD  (default admin123456)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests

LOBBY_URL = os.environ.get(
    "GUANDAN_E2E_LOBBY_URL", "http://127.0.0.1:8686"
).rstrip("/")
ADMIN_PASSWORD = os.environ.get("GUANDAN_E2E_ADMIN_PASSWORD", "admin123456")

PY_GUANDAN_ROOT = Path(__file__).resolve().parent.parent


def _lobby_reachable() -> bool:
    try:
        resp = requests.get(f"{LOBBY_URL}/internal/health", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _login() -> str:
    resp = requests.post(
        f"{LOBBY_URL}/api/auth/login",
        json={"account": "admin", "password": ADMIN_PASSWORD},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"admin login failed: HTTP {resp.status_code}: {resp.text}"
    )
    return resp.json()["tokens"]["accessToken"]["token"]


def _create_automation_key(session_token: str) -> str:
    resp = requests.post(
        f"{LOBBY_URL}/api/v1/developer/keys",
        headers={
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
        },
        json={
            "name": "e2e benchmark run",
            "environment": "test",
            "scopes": ["benchmarks:create"],
        },
        timeout=10,
    )
    assert resp.status_code == 201, (
        f"key creation failed: HTTP {resp.status_code}: {resp.text}"
    )
    return resp.json()["api_key"]


@pytest.mark.skipif(
    not _lobby_reachable(),
    reason="lobby server not running (set GUANDAN_E2E_LOBBY_URL)",
)
def test_script_run_appears_in_benchmark_history() -> None:
    session_token = _login()
    api_key = _create_automation_key(session_token)
    benchmark_name = f"E2E script run {int(time.time())}"

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.yaml"
        config_path.write_text(
            f"""
developer_api_key: {api_key}
lobby_url: {LOBBY_URL}
name: {benchmark_name}
num_rounds: 2
# 2 rounds of strongBot can legitimately take several minutes (a slow
# round 2 has been observed to run past 300 s), so give the run the same
# headroom the Dart E2E uses.
total_timeout: 900
heartbeat_timeout: 60
bots:
  seat_1: {{type: builtin, bot_code: strongBot}}
  seat_2: {{type: builtin, bot_code: strongBot}}
  seat_3: {{type: builtin, bot_code: strongBot}}
  seat_4: {{type: builtin, bot_code: strongBot}}
""",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [sys.executable, "-m", "guandan_benchmark", "--config", str(config_path)],
            cwd=PY_GUANDAN_ROOT,
            capture_output=True,
            text=True,
            # Covers the 900 s total_timeout plus startup margin.
            timeout=1020,
        )
        assert proc.returncode == 0, (
            f"benchmark script failed (rc={proc.returncode}):\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

        match = re.search(r"benchmark_id:\s+([A-Z0-9]{8})", proc.stdout)
        assert match is not None, (
            f"no benchmark_id in script output:\n{proc.stdout}"
        )
        benchmark_id = match.group(1)

    # Poll the session-authenticated detail endpoint until completed.
    headers = {"Authorization": f"Bearer {session_token}"}
    deadline = time.time() + 120
    detail: dict = {}
    while time.time() < deadline:
        resp = requests.get(
            f"{LOBBY_URL}/api/benchmarks/{benchmark_id}",
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, (
            f"benchmark detail failed: HTTP {resp.status_code}: {resp.text}"
        )
        detail = resp.json()
        if detail.get("status") in ("completed", "failed", "cancelled"):
            break
        time.sleep(2)

    assert detail.get("status") == "completed", (
        f"benchmark did not complete: {json.dumps(detail, indent=2)}"
    )
    assert detail.get("benchmark_name") == benchmark_name
    assert detail.get("round_results") is not None
    assert len(detail["round_results"]) == 2, (
        f"expected 2 round results, got {len(detail['round_results'])}"
    )
    summary = detail.get("summary") or {}
    assert summary.get("rounds_completed") == 2
    assert summary.get("red_wins", 0) + summary.get("blue_wins", 0) == 2

    # The history list (what the Developer Center tab shows) also contains it.
    resp = requests.get(
        f"{LOBBY_URL}/api/benchmarks?limit=50",
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    listed_ids = [b["benchmark_id"] for b in resp.json()["benchmarks"]]
    assert benchmark_id in listed_ids
