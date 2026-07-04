from guandan_bot._websocket import loopback_proxy_options


def modern_connect(uri: str, *, proxy=True):
    pass


def legacy_connect(uri: str, **kwargs):
    pass


def test_loopback_websocket_bypasses_automatic_proxy() -> None:
    assert loopback_proxy_options(modern_connect, "ws://127.0.0.1:9001/path") == {
        "proxy": None
    }
    assert loopback_proxy_options(modern_connect, "ws://[::1]:9001/path") == {
        "proxy": None
    }
    assert loopback_proxy_options(modern_connect, "ws://localhost:9001/path") == {
        "proxy": None
    }


def test_remote_websocket_keeps_automatic_proxy_configuration() -> None:
    assert loopback_proxy_options(modern_connect, "wss://game.example/path") == {}


def test_legacy_websockets_does_not_receive_unsupported_proxy_option() -> None:
    assert loopback_proxy_options(legacy_connect, "ws://127.0.0.1:9001/path") == {}
