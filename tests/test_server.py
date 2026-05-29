from custom_components.aruba_ble_proxy.server import ArubaBleReceiver


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
