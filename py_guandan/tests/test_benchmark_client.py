from py_guandan.http import GuandanHttpClient


def test_benchmark_http_session_ignores_proxies_for_loopback_only() -> None:
    client = GuandanHttpClient()
    assert client.session_for("http://127.0.0.1:8686").trust_env is False
    assert client.session_for("http://localhost:9001").trust_env is False
    assert client.session_for("https://example.com").trust_env is True
    client.close()
