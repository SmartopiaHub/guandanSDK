import benchmark


def test_api_request_uses_central_http_client(monkeypatch) -> None:
    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"ok": True}

    monkeypatch.setattr(benchmark.http_client, "request_json", request_json)

    result = benchmark.api_request(
        "POST",
        "http://127.0.0.1:8686/api/auth/login",
        body={"account": "user", "password": "password"},
    )

    assert result == {"ok": True}
    assert requests[0][0:2] == (
        "POST",
        "http://127.0.0.1:8686/api/auth/login",
    )
