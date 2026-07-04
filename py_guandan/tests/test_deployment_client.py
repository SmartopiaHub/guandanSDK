from guandan_bot.deployment import BotDeploymentClient


def test_client_uses_central_http_client(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"providers": []}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)

    client = BotDeploymentClient(
        lobby_url="http://127.0.0.1:8686",
        api_key="test-key",
    )

    assert client.list_providers() == {"providers": []}
    assert requests[0][0:2] == (
        "GET",
        "http://127.0.0.1:8686/api/v1/developer/bots/providers",
    )
