import ast
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from py_guandan.http import GuandanHttpClient, is_loopback_url


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8686",
        "http://service.localhost:8686",
        "http://127.0.0.1:8686",
        "http://127.42.0.1:8686",
        "http://[::1]:8686",
    ],
)
def test_loopback_url_detection(url) -> None:
    assert is_loopback_url(url)


def test_loopback_request_bypasses_poisoned_proxy(monkeypatch) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = GuandanHttpClient()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.delenv("NO_PROXY", raising=False)

    try:
        result = client.request_json(
            "GET",
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=2,
        )
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result == {"status": "ok"}


def test_sessions_enable_tcp_nodelay() -> None:
    """Every pooled connection must set TCP_NODELAY.

    The game server writes SSE events as one small write per event.  Without
    TCP_NODELAY the client's delayed ACKs let the server's kernel hold small
    writes until the next write flushes them, so heartbeats arrive one
    period late and the final event of a stream (e.g. ``test.completed``)
    is never delivered at all — the benchmark monitor would hang.  Both
    sessions (proxy-aware and loopback-direct) must apply the socket
    option to every pooled connection.
    """
    client = GuandanHttpClient()
    try:
        for session in (client._normal_session, client._direct_session):
            adapter = session.get_adapter("http://")
            pool_kw = adapter.poolmanager.connection_pool_kw
            options = pool_kw.get("socket_options")
            assert options is not None, f"no socket_options in pool for {session}"
            assert (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) in options
    finally:
        client.close()


def test_production_code_has_no_direct_http_clients() -> None:
    root = Path(__file__).resolve().parents[1]
    transport_path = root / "py_guandan" / "http.py"
    violations = []

    for path in root.rglob("*.py"):
        if (
            path == transport_path
            or "tests" in path.parts
            or ".venv" in path.parts  # third-party packages, not production code
        ):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == "requests" for alias in node.names):
                    violations.append(f"{path}: direct requests import")
            elif isinstance(node, ast.ImportFrom):
                if node.module in {"requests", "urllib.request"}:
                    violations.append(f"{path}: direct {node.module} import")

    assert violations == []
