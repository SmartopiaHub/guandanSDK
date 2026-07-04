import asyncio

from guandan_bot import AsyncBotRequest, AsyncHttpBotServer, AsyncWebSocketBotClient
from py_guandan.http import http_client


def test_async_http_server_delegates_protocol_messages() -> None:
    requests = []

    async def handler(request: AsyncBotRequest):
        requests.append(request)
        return {"type": "accepted", "session_id": request.session_id}

    async def scenario() -> None:
        server = AsyncHttpBotServer(
            handler,
            host="127.0.0.1",
            port=0,
            invocation_key="secret",
        )
        await server.start()
        base_url = f"http://127.0.0.1:{server.port}"
        try:
            unauthorized = await asyncio.to_thread(
                http_client.request,
                "POST",
                f"{base_url}/sessions",
                json={"type": "session_start", "session_id": "s1"},
            )
            assert unauthorized.status_code == 401

            response = await asyncio.to_thread(
                http_client.request_json,
                "POST",
                f"{base_url}/sessions",
                body={"type": "session_start", "session_id": "s1"},
                headers={"Authorization": "Bearer secret"},
            )
            assert response == {"type": "accepted", "session_id": ""}
            assert requests[0].create_session is True

            await asyncio.to_thread(
                http_client.request_json,
                "DELETE",
                f"{base_url}/sessions/s1",
                headers={"X-Api-Key": "secret"},
            )
            assert requests[1].end_session is True
            assert requests[1].session_id == "s1"
        finally:
            await server.stop()

    asyncio.run(scenario())


def test_async_websocket_client_delegates_and_sends_response() -> None:
    requests = []
    sent = []

    async def handler(request: AsyncBotRequest):
        requests.append(request)
        return {"type": "session_started", "session_id": "s1"}

    class Socket:
        async def send(self, value):
            sent.append(value)

    async def scenario() -> None:
        client = AsyncWebSocketBotClient(
            handler,
            game_server_url="http://127.0.0.1:9001",
            deployment_key="secret",
        )
        client._socket = Socket()
        await client._handle_frame('{"type":"session_start","session_id":"s1"}')

    asyncio.run(scenario())
    assert requests[0].create_session is True
    assert '"type": "session_started"' in sent[0]
