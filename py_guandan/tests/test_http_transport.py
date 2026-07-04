import json
import threading
import ast
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


def test_production_code_has_no_direct_http_clients() -> None:
    root = Path(__file__).resolve().parents[1]
    transport_path = root / "py_guandan" / "http.py"
    violations = []

    for path in root.rglob("*.py"):
        if path == transport_path or "tests" in path.parts:
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
