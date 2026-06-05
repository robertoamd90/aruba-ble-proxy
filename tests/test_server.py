import asyncio

import pytest

from custom_components.aruba_ble_proxy.server import ArubaBleReceiver
from custom_components.aruba_ble_proxy import server as server_module


def test_receiver_forget_connection_returns_only_sources_lost_by_that_socket():
    receiver = ArubaBleReceiver(access_token="secret")
    old_socket = object()
    new_socket = object()

    receiver._track_connection_source(old_socket, "02:00:00:00:00:01")
    receiver._track_connection_source(old_socket, "02:00:00:00:00:02")
    receiver._track_connection_source(new_socket, "02:00:00:00:00:01")

    disconnected = receiver._forget_connection(old_socket)

    assert disconnected == ["02:00:00:00:00:02"]
    assert receiver.connected_sources() == ["02:00:00:00:00:01"]


def test_receiver_source_disconnect_handler_is_invoked():
    disconnected = []
    receiver = ArubaBleReceiver(
        access_token="secret",
        source_disconnect_handler=disconnected.append,
    )

    receiver._notify_source_disconnected("02:00:00:00:00:01")

    assert disconnected == ["02:00:00:00:00:01"]


def test_receiver_send_to_source_times_out(monkeypatch):
    class WebSocket:
        async def send(self, payload):
            await asyncio.Future()

    async def run_test():
        receiver = ArubaBleReceiver(access_token="secret")
        receiver._track_connection_source(WebSocket(), "02:00:00:00:00:01")
        monkeypatch.setattr(server_module, "SEND_TIMEOUT", 0.001)

        with pytest.raises(TimeoutError):
            await receiver.async_send_to_source("02:00:00:00:00:01", b"payload")

    asyncio.run(run_test())
