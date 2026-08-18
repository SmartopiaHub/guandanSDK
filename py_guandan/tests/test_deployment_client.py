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


def test_http_deployment_can_include_base_url(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"deployment_id": "DABCDEFG"}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)
    client = BotDeploymentClient("http://127.0.0.1:8686", "test-key")
    client.create_deployment(
        "PABCDE",
        "http",
        ["BABCDE"],
        base_url="http://127.0.0.1:10001",
    )

    assert requests[0][2]["body"]["base_url"] == "http://127.0.0.1:10001"


def test_create_definition_can_include_parameter_schema(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"definition": {"bot_definition_id": "B1"}}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)
    client = BotDeploymentClient("http://127.0.0.1:8686", "test-key")
    schema = [
        {"name": "strength", "type": "integer", "default": 50, "min": 0},
        {"name": "aggressive", "type": "boolean", "default": False},
    ]
    client.create_definition(
        "P1", "Example Bot", "1.0.0", "exampleBot", parameters=schema
    )

    assert requests[0][2]["body"]["parameters"] == schema


def test_create_definition_omits_parameters_by_default(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"definition": {"bot_definition_id": "B1"}}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)
    client = BotDeploymentClient("http://127.0.0.1:8686", "test-key")
    client.create_definition("P1", "Example Bot", "1.0.0", "exampleBot")

    assert "parameters" not in requests[0][2]["body"]


def test_create_deployment_can_include_parameter_values(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"deployment": {"deployment_id": "D1"}}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)
    client = BotDeploymentClient("http://127.0.0.1:8686", "test-key")
    client.create_deployment(
        "P1",
        "websocket",
        ["B1"],
        parameter_values={"strength": 25},
    )

    assert requests[0][2]["body"]["parameter_values"] == {"strength": 25}


def test_create_deployment_omits_parameter_values_by_default(monkeypatch) -> None:
    from guandan_bot import deployment

    requests = []

    def request_json(method, url, **kwargs):
        requests.append((method, url, kwargs))
        return {"deployment": {"deployment_id": "D1"}}

    monkeypatch.setattr(deployment.http_client, "request_json", request_json)
    client = BotDeploymentClient("http://127.0.0.1:8686", "test-key")
    client.create_deployment("P1", "websocket", ["B1"])

    assert "parameter_values" not in requests[0][2]["body"]
