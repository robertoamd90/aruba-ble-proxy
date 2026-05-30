import asyncio

from custom_components.aruba_ble_proxy.active import (
    ACTION_BLE_CONNECT,
    ACTION_BLE_DISCONNECT,
    ACTION_GATT_NOTIFICATION,
    ArubaBleActionRequest,
)
from custom_components.aruba_ble_proxy.aruba_proto import ArubaTelemetryMessage
from custom_components.aruba_ble_proxy.models import (
    ArubaActionResult,
    ArubaActionStatus,
    ArubaBleEvent,
    ArubaCharacteristic,
    ArubaStatusUpdate,
    BleAdvertisement,
    BleFrameType,
    MacAddrType,
    Reporter,
)
from custom_components.aruba_ble_proxy.const import (
    CONF_AP_SOURCE,
    CONF_ENTRY_TYPE,
    CONF_PARENT_ENTRY_ID,
    DOMAIN,
    ENTRY_TYPE_AP_SOURCE,
)
from custom_components.aruba_ble_proxy import runtime as runtime_module
from custom_components.aruba_ble_proxy.runtime import ArubaBleProxyRuntime


def _event() -> ArubaBleEvent:
    return ArubaBleEvent(
        reporter=Reporter(
            name="ap-1",
            mac="02:00:00:00:00:01",
            ipv4="192.0.2.10",
            ipv6=None,
            hardware_type="AP-515",
            software_version="8.13.2.0",
            software_build=None,
            timestamp=None,
        ),
        address="02:00:00:00:01:03",
        frame_type=BleFrameType.ADV_IND,
        rssi=-61,
        address_type=MacAddrType.PUBLIC,
        apb_mac=None,
        payload=b"\x02\x01\x06",
        advertisement=BleAdvertisement(
            local_name="LYWSD03MMC",
            service_data={"0000fcd2-0000-1000-8000-00805f9b34fb": b"\x03\x04"},
            manufacturer_data={0x0959: b"\x01\x02"},
        ),
    )


def _reporter(mac: str) -> Reporter:
    return Reporter(
        name=None,
        mac=mac,
        ipv4=None,
        ipv6=None,
        hardware_type=None,
        software_version=None,
        software_build=None,
        timestamp=None,
    )


def test_runtime_tracks_last_advertisement_diagnostics():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )

    runtime._update_stats(_event())

    diagnostics = runtime.diagnostic_attributes()

    assert diagnostics["events"] == 1
    assert diagnostics["addresses"] == 1
    assert diagnostics["last_address"] == "02:00:00:00:01:03"
    assert diagnostics["last_source"] == "02:00:00:00:00:01"
    assert diagnostics["last_rssi"] == -61
    assert diagnostics["last_local_name"] == "LYWSD03MMC"
    assert diagnostics["last_service_data"] == ["0000fcd2-0000-1000-8000-00805f9b34fb"]
    assert diagnostics["last_manufacturer_ids"] == [0x0959]
    assert diagnostics["last_seen"]


def test_runtime_throttles_passive_listener_updates(monkeypatch):
    monkeypatch.setattr(runtime_module, "PASSIVE_SENSOR_UPDATE_INTERVAL", 60.0)
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )
    notifications = 0

    def listener():
        nonlocal notifications
        notifications += 1

    runtime.async_add_listener(listener)

    async def run_events():
        await runtime._async_handle_event(_event())
        await runtime._async_handle_event(_event())
        await runtime._async_handle_event(_event())

    asyncio.run(run_events())

    assert runtime.stats.events == 3
    assert notifications == 1


def test_runtime_tracks_advertised_service_uuids_by_device():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )
    event = _event()
    event = ArubaBleEvent(
        reporter=event.reporter,
        address="020000000101",
        frame_type=event.frame_type,
        rssi=event.rssi,
        address_type=event.address_type,
        apb_mac=event.apb_mac,
        payload=event.payload,
        advertisement=BleAdvertisement(
            local_name="Lock Pro",
            service_data={"fd3d": b"\x01"},
            manufacturer_data={},
        ),
    )

    runtime._update_stats(event)

    assert runtime.service_uuids_for_device("02:00:00:00:01:01") == {
        "0000fd3d-0000-1000-8000-00805f9b34fb"
    }


def test_runtime_unknown_device_is_not_active():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )

    assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False
    assert runtime.active_devices_for_source("02:00:00:00:00:01") == []


def test_runtime_creates_distinct_ap_source_entries_for_remote_scanners():
    async def run_test():
        class Entry:
            def __init__(self, entry_id, data):
                self.entry_id = entry_id
                self.data = data

        class Flow:
            def __init__(self, entries):
                self.entries = entries
                self.calls = []

            async def async_init(self, domain, *, context, data):
                self.calls.append((domain, context, data))
                entry = Entry(f"ap-entry-{len(self.entries) + 1}", dict(data))
                self.entries.append(entry)
                return {"type": "create_entry", "result": entry}

        class ConfigEntries:
            def __init__(self):
                self.entries = []
                self.flow = Flow(self.entries)

            def async_entries(self, domain):
                assert domain == DOMAIN
                return list(self.entries)

            def async_get_entry(self, entry_id):
                return next(
                    (entry for entry in self.entries if entry.entry_id == entry_id),
                    None,
                )

        class Hass:
            def __init__(self):
                self.config_entries = ConfigEntries()

        hass = Hass()
        runtime = ArubaBleProxyRuntime(
            hass=hass,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._entry_id = "listener-entry"

        first = await runtime._async_source_config_entry_id("02:00:00:00:00:01")
        second = await runtime._async_source_config_entry_id("02:00:00:00:00:02")
        first_again = await runtime._async_source_config_entry_id("02:00:00:00:00:01")

        assert first == "ap-entry-1"
        assert second == "ap-entry-2"
        assert first_again == "ap-entry-1"
        assert len(hass.config_entries.flow.calls) == 2
        assert hass.config_entries.entries[0].data == {
            CONF_ENTRY_TYPE: ENTRY_TYPE_AP_SOURCE,
            CONF_AP_SOURCE: "02:00:00:00:00:01",
            CONF_PARENT_ENTRY_ID: "listener-entry",
        }
        assert hass.config_entries.entries[1].data == {
            CONF_ENTRY_TYPE: ENTRY_TYPE_AP_SOURCE,
            CONF_AP_SOURCE: "02:00:00:00:00:02",
            CONF_PARENT_ENTRY_ID: "listener-entry",
        }

    asyncio.run(run_test())


def test_runtime_falls_back_when_remote_scanner_registration_fails(monkeypatch):
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )
    payloads = []

    def callback(payload):
        payloads.append(payload)

    def fail_register(*args, **kwargs):
        raise RuntimeError("scanner unavailable")

    monkeypatch.setattr("custom_components.aruba_ble_proxy.runtime._payload_to_ha_service_info", lambda payload: payload)
    runtime._register_scanner = fail_register
    runtime._bluetooth_callback = callback

    # _async_handle_event should try the remote scanner path, observe the
    # registration failure, and then fall back to the generic advertisement
    # callback.
    asyncio.run(runtime._async_handle_event(_event()))

    assert len(payloads) == 1
    assert runtime.stats.bluetooth_forward_errors == 1
    assert runtime.stats.bluetooth_forwards == 1
    assert runtime.stats.last_bluetooth_error is None


def test_runtime_sends_active_action_and_waits_for_result():
    async def run_test():
        loop = asyncio.get_running_loop()

        class Hass:
            pass

        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        hass = Hass()
        hass.loop = loop
        runtime = ArubaBleProxyRuntime(
            hass=hass,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-1",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)

        assert receiver.payloads
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-1",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        response = await task
        assert response["sent"] is True
        assert response["result"]["received"] is True
        assert response["result"]["status"] == "success"
        assert runtime.stats.active_actions_sent == 1
        assert runtime.stats.active_action_results == 1
        assert runtime.stats.last_active_action_type == ACTION_BLE_CONNECT
        assert runtime.stats.last_active_action_duration_ms is not None
        assert runtime.stats.slowest_active_action_type == ACTION_BLE_CONNECT
        assert runtime.stats.slowest_active_action_status == "success"

    asyncio.run(run_test())


def test_runtime_treats_idempotent_connect_disconnect_results_as_success():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        connect_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-idempotent",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-idempotent",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="alreadyConnected",
                        status_string="already connected",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        connect_response = await connect_task
        assert connect_response["result"]["status"] == "alreadyConnected"
        assert runtime.stats.active_action_failures == 0
        assert runtime.active_devices_for_source("02:00:00:00:00:01") == [
            "02:00:00:00:01:01"
        ]

        disconnect_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_DISCONNECT,
                    action_id="disconnect-idempotent",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="disconnect-idempotent",
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="notConnected",
                        status_string="not connected",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        disconnect_response = await disconnect_task
        assert disconnect_response["result"]["status"] == "notConnected"
        assert runtime.stats.active_action_failures == 0
        assert runtime.active_devices_for_source("02:00:00:00:00:01") == []

    asyncio.run(run_test())


def test_runtime_rejects_second_active_connect_on_same_ap_locally():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}

        response = await runtime.async_send_aruba_action(
            ap_mac="02:00:00:00:00:01",
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                action_id="connect-second-device",
                device_mac="02:00:00:00:01:02",
            ),
        )

        assert response["sent"] is False
        assert response["status"] == "noMoreConnectionSlots"
        assert response["ap_mac"] == "02:00:00:00:00:01"
        assert response["device_mac"] == "02:00:00:00:01:02"
        assert receiver.payloads == []
        assert runtime.stats.active_actions_sent == 0
        assert runtime.stats.active_action_failures == 1
        assert runtime.stats.last_active_action_status == "noMoreConnectionSlots"
        assert runtime.stats.last_active_action_error == (
            "noMoreConnectionSlots: "
            "Another BLE device is already connected through this Aruba AP"
        )

    asyncio.run(run_test())


def test_runtime_allows_second_active_connect_when_slots_are_configured():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
            active_connection_slots=2,
        )
        receiver = Receiver()
        runtime._receiver = receiver
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-second-device",
                    device_mac="02:00:00:00:01:02",
                ),
            )
        )
        await asyncio.sleep(0)

        assert len(receiver.payloads) == 1
        assert runtime.can_connect_source("02:00:00:00:00:01") is False

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-second-device",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:02",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        response = await task
        assert response["sent"] is True
        assert response["result"]["status"] == "success"
        assert runtime.diagnostic_attributes()["active_connection_slots_per_ap"] == 2

    asyncio.run(run_test())


def test_runtime_treats_duplicate_active_connect_on_same_ap_as_local_success():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}

        response = await runtime.async_send_aruba_action(
            ap_mac="02:00:00:00:00:01",
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                action_id="connect-same-device",
                device_mac="02:00:00:00:01:01",
            ),
        )

        assert response["sent"] is False
        assert response["status"] == "alreadyConnected"
        assert response["device_mac"] == "02:00:00:00:01:01"
        assert receiver.payloads == []
        assert runtime.stats.active_actions_sent == 0
        assert runtime.stats.active_action_failures == 0
        assert runtime.stats.last_active_action_status == "alreadyConnected"
        assert runtime.stats.last_active_action_error is None

    asyncio.run(run_test())


def test_runtime_uses_pending_context_for_incomplete_success_result():
    async def run_test():
        class Hass:
            pass

        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=Hass(),
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-1",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-1",
                        action_type=None,
                        device_mac=None,
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        response = await task

        assert response["result"]["status"] == "success"
        assert response["result"]["device_mac"] == "02:00:00:00:01:01"
        assert runtime._active_device_keys_by_source == {
            "02:00:00:00:00:01": {
                ("02:00:00:00:00:01", "02:00:00:00:01:01")
            }
        }

    asyncio.run(run_test())


def test_runtime_gatt_read_waits_for_characteristic_value():
    async def run_test():
        class Hass:
            pass

        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=Hass(),
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
            )
        )
        await asyncio.sleep(0)
        assert runtime.diagnostic_attributes()["active_pending_characteristic_reads"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "waiters": 1,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type="gattRead",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )

        response = await task
        assert response["result"]["status"] == "success"
        assert response["characteristic"]["received"] is True
        assert response["characteristic"]["value"] == "64"
        assert runtime.stats.active_characteristics == 1
        assert runtime.stats.last_active_characteristic_value == "64"

    asyncio.run(run_test())


def test_runtime_gatt_read_matches_short_uuid_to_full_characteristic_uuid():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="180f",
                characteristic_uuid="2a19",
            )
        )
        await asyncio.sleep(0)
        assert runtime.diagnostic_attributes()["active_pending_characteristic_reads"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "waiters": 1,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type="gattRead",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )

        response = await task
        assert response["characteristic"]["received"] is True
        assert response["characteristic"]["value"] == "64"

    asyncio.run(run_test())


def test_runtime_gatt_read_characteristics_are_source_scoped():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01", "02:00:00:00:00:02"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        read_1 = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=1,
            )
        )
        read_2 = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:02",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=1,
            )
        )
        await asyncio.sleep(0)

        action_ids = {
            context.ap_mac: action_id
            for action_id, context in runtime._pending_action_contexts.items()
        }
        for source, action_id in action_ids.items():
            await runtime._async_handle_message(
                ArubaTelemetryMessage(
                    reporter=_reporter(source),
                    events=[],
                    action_results=[
                        ArubaActionResult(
                            reporter=_reporter(source),
                            action_id=action_id,
                            action_type="gattRead",
                            device_mac="02:00:00:00:01:01",
                            status=ArubaActionStatus.SUCCESS,
                            status_name="success",
                            status_string="ok",
                            apb_mac=None,
                        )
                    ],
                    characteristics=[],
                )
            )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_reporter("02:00:00:00:00:01"),
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_reporter("02:00:00:00:00:01"),
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )
        await asyncio.sleep(0)
        assert read_1.done()
        assert not read_2.done()

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_reporter("02:00:00:00:00:02"),
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_reporter("02:00:00:00:00:02"),
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x65",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )

        assert (await read_1)["characteristic"]["value"] == "64"
        assert (await read_2)["characteristic"]["value"] == "65"

    asyncio.run(run_test())


def test_runtime_gatt_read_without_wait_result_returns_immediately():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver

        response = await runtime.async_gatt_read(
            ap_mac="02:00:00:00:00:01",
            device_mac="02:00:00:00:01:01",
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
            timeout=20,
            wait_result=False,
        )

        assert response["sent"] is True
        assert response["action_type"] == "gattRead"
        assert "result" not in response
        assert "characteristic" not in response
        assert len(receiver.payloads) == 1
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}
        assert runtime._pending_characteristics == {}
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_late_connect_result_without_wait_result_marks_device_active():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        response = await runtime.async_send_aruba_action(
            ap_mac="02:00:00:00:00:01",
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                action_id="connect-no-wait",
                device_mac="02:00:00:00:01:01",
            ),
            wait_result=False,
        )

        assert response["sent"] is True
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-no-wait",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        assert runtime.stats.active_action_orphan_results == 1
        assert runtime.stats.active_action_failures == 0
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is True

    asyncio.run(run_test())


def test_runtime_late_disconnect_result_without_wait_result_marks_device_disconnected():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}

        response = await runtime.async_send_aruba_action(
            ap_mac="02:00:00:00:00:01",
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_DISCONNECT,
                action_id="disconnect-no-wait",
                device_mac="02:00:00:00:01:01",
            ),
            wait_result=False,
        )

        assert response["sent"] is True
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is True

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="disconnect-no-wait",
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        assert runtime.stats.active_action_orphan_results == 1
        assert runtime.stats.active_action_failures == 0
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False
        assert runtime.diagnostic_attributes()["active_disconnected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "status": "deviceDisconnected",
            }
        ]

    asyncio.run(run_test())


def test_runtime_gatt_write_sends_write_action():
    async def run_test():
        class Hass:
            pass

        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=Hass(),
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver

        task = asyncio.create_task(
            runtime.async_gatt_write(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                value=b"\x01",
                with_response=True,
            )
        )
        await asyncio.sleep(0)

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type="gattWriteWithResponse",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        response = await task
        assert response["result"]["status"] == "success"
        assert runtime.stats.active_actions_sent == 1

    asyncio.run(run_test())


def test_runtime_serializes_gatt_operations_until_read_value_arrives():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver

        read_task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=1,
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1
        read_action_id = runtime.stats.last_active_action_id or ""

        write_task = asyncio.create_task(
            runtime.async_gatt_write(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                value=b"\x01",
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_operation_locks"] == 1
        assert diagnostics["active_operations_in_flight"] == 1
        assert diagnostics["active_operations_waiting"] == 1
        assert diagnostics["active_pending_actions"] == [
            {
                "action_id": read_action_id,
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "action_type": "gattRead",
            }
        ]
        assert diagnostics["active_pending_characteristic_reads"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "waiters": 1,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=read_action_id,
                        action_type="gattRead",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )
        read_response = await read_task
        assert read_response["characteristic"]["value"] == "64"

        await asyncio.sleep(0)
        assert len(receiver.payloads) == 2
        write_action_id = runtime.stats.last_active_action_id or ""
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=write_action_id,
                        action_type="gattWriteWithResponse",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        write_response = await write_task
        assert write_response["result"]["status"] == "success"
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_operation_locks"] == 0
        assert diagnostics["active_operations_in_flight"] == 0
        assert diagnostics["active_operations_waiting"] == 0
        assert diagnostics["active_pending_actions"] == []
        assert diagnostics["active_pending_characteristic_reads"] == []

    asyncio.run(run_test())


def test_runtime_serializes_active_operations_per_ap_source():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
            active_connection_slots=2,
        )
        receiver = Receiver()
        runtime._receiver = receiver

        first_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-one",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1

        second_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-two",
                    device_mac="02:00:00:00:01:02",
                ),
            )
        )
        await asyncio.sleep(0)

        assert len(receiver.payloads) == 1
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_operation_locks"] == 1
        assert diagnostics["active_operations_in_flight"] == 1
        assert diagnostics["active_operations_waiting"] == 1
        assert runtime.pending_connect_devices_for_source("02:00:00:00:00:01") == [
            "02:00:00:00:01:01"
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-one",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    ),
                ],
                characteristics=[],
            )
        )
        assert (await first_task)["result"]["status"] == "success"

        await asyncio.sleep(0)
        assert len(receiver.payloads) == 2
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-two",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:02",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    ),
                ],
                characteristics=[],
            )
        )
        assert (await second_task)["result"]["status"] == "success"
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_serializes_active_operations_for_same_device():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
            active_connection_slots=2,
        )
        receiver = Receiver()
        runtime._receiver = receiver

        first_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-one",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1

        second_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-two",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)

        assert len(receiver.payloads) == 1
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_operation_locks"] == 1
        assert diagnostics["active_operations_in_flight"] == 1
        assert diagnostics["active_operations_waiting"] == 1

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-one",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        assert (await first_task)["result"]["status"] == "success"

        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1
        second_response = await second_task
        assert second_response["sent"] is False
        assert second_response["status"] == "alreadyConnected"
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_counts_pending_connects_against_connection_slots():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
            active_connection_slots=1,
        )
        receiver = Receiver()
        runtime._receiver = receiver

        first_task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-one",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1
        assert runtime.can_connect_source("02:00:00:00:00:01") is False

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-one",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        assert (await first_task)["result"]["status"] == "success"

    asyncio.run(run_test())


def test_runtime_waits_for_device_characteristics():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        wait_task = asyncio.create_task(
            runtime.async_wait_for_device_characteristics(
                "02:00:00:00:01:01",
                timeout=1,
            )
        )
        await asyncio.sleep(0)
        assert runtime.diagnostic_attributes()["active_pending_device_discoveries"] == [
            {
                "source": None,
                "device_mac": "02:00:00:00:01:01",
                "waiters": 1,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
            )
        )

        characteristics = await wait_task
        assert len(characteristics) == 1
        assert characteristics[0].value == b"\x64"
        assert runtime.stats.active_characteristic_waits == 1
        assert runtime.stats.active_characteristic_wait_timeouts == 0
        assert runtime.stats.last_active_characteristic_wait_status == "received"
        assert runtime.stats.last_active_characteristic_wait_duration_ms is not None
        assert runtime.stats.slowest_active_characteristic_wait_status == "received"
        assert runtime.diagnostic_attributes()["active_pending_device_discoveries"] == []

    asyncio.run(run_test())


def test_runtime_device_characteristics_wait_times_out_cleanly():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        characteristics = await runtime.async_wait_for_device_characteristics(
            "02:00:00:00:01:01",
            timeout=0.01,
        )

        assert characteristics == []
        assert runtime.stats.active_characteristic_waits == 1
        assert runtime.stats.active_characteristic_wait_timeouts == 1
        assert runtime.stats.last_active_characteristic_wait_status == "timeout"
        assert runtime.stats.last_active_characteristic_wait_duration_ms is not None
        assert runtime.stats.slowest_active_characteristic_wait_status == "timeout"
        assert runtime._pending_device_characteristics == {}

    asyncio.run(run_test())


def test_runtime_gatt_notification_invokes_callback_and_stops():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        updates = []

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        def callback(characteristic):
            updates.append(characteristic.value)

        start_task = asyncio.create_task(
            runtime.async_start_gatt_notify(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                callback=callback,
            )
        )
        await asyncio.sleep(0)

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type=ACTION_GATT_NOTIFICATION,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        start_response = await start_task
        assert start_response["result"]["status"] == "success"
        assert runtime.stats.active_notifications_enabled == 1
        assert runtime.diagnostic_attributes()["active_notification_subscriptions"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "callbacks": 1,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x65",
                        description="Battery Level",
                        properties=("notify",),
                    )
                ],
            )
        )

        assert updates == [b"\x65"]
        assert runtime.stats.active_notification_updates == 1

        stop_task = asyncio.create_task(
            runtime.async_stop_gatt_notify(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                callback=callback,
            )
        )
        await asyncio.sleep(0)
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type=ACTION_GATT_NOTIFICATION,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        stop_response = await stop_task
        assert stop_response["result"]["status"] == "success"
        assert runtime.stats.active_notifications_enabled == 0
        assert runtime.diagnostic_attributes()["active_notification_subscriptions"] == []

    asyncio.run(run_test())


def test_runtime_registers_local_notify_callback_without_aruba_action():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )

    values = []
    registered = runtime.register_gatt_notify_callback(
        ap_mac="02:00:00:00:00:01",
        device_mac="02:00:00:00:01:01",
        service_uuid="cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
        callback=lambda characteristic: values.append(characteristic.value),
    )

    assert registered is True
    assert runtime.stats.active_notifications_enabled == 1

    runtime._handle_characteristic(
        ArubaCharacteristic(
            reporter=_reporter("02:00:00:00:00:01"),
            device_mac="02:00:00:00:01:01",
            service_uuid="cba20d00-224d-11e6-9fb8-0002a5d5c51b",
            characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
            value=b"\x01",
            description=None,
            properties=("notify",),
        )
    )

    assert values == [b"\x01"]


def test_runtime_local_notify_callback_matches_characteristic_without_service_uuid():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )

    values = []
    runtime.register_gatt_notify_callback(
        ap_mac="02:00:00:00:00:01",
        device_mac="02:00:00:00:01:01",
        service_uuid="cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
        callback=lambda characteristic: values.append(characteristic.value),
    )

    runtime._handle_characteristic(
        ArubaCharacteristic(
            reporter=_reporter("02:00:00:00:00:01"),
            device_mac="02:00:00:00:01:01",
            service_uuid=None,
            characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
            value=b"\x0f",
            description=None,
            properties=("notify",),
        )
    )

    assert values == [b"\x0f"]
    assert runtime.stats.active_notification_updates == 1


def test_runtime_local_notify_callback_matches_characteristic_service_mismatch():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )

    values = []
    runtime.register_gatt_notify_callback(
        ap_mac="02:00:00:00:00:01",
        device_mac="02:00:00:00:01:01",
        service_uuid="cba20d00-224d-11e6-9fb8-0002a5d5c51b",
        characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
        callback=lambda characteristic: values.append(characteristic.value),
    )

    runtime._handle_characteristic(
        ArubaCharacteristic(
            reporter=_reporter("02:00:00:00:00:01"),
            device_mac="02:00:00:00:01:01",
            service_uuid="0000180a-0000-1000-8000-00805f9b34fb",
            characteristic_uuid="cba20003-224d-11e6-9fb8-0002a5d5c51b",
            value=b"\x0f",
            description=None,
            properties=("notify",),
        )
    )

    assert values == [b"\x0f"]
    assert runtime.stats.active_notification_updates == 1


def test_runtime_notification_callback_error_is_isolated():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        key = (
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            "0000180f-0000-1000-8000-00805f9b34fb",
            "00002a19-0000-1000-8000-00805f9b34fb",
        )
        updates = []

        def failing_callback(characteristic):
            raise RuntimeError("callback boom")

        def working_callback(characteristic):
            updates.append(characteristic.value)

        runtime._notification_callbacks[key] = [failing_callback, working_callback]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x66",
                        description="Battery Level",
                        properties=("notify",),
                    )
                ],
            )
        )

        assert updates == [b"\x66"]
        assert runtime.stats.active_notification_callback_errors == 1
        assert "callback boom" in (runtime.stats.last_active_notification_error or "")

    asyncio.run(run_test())


def test_runtime_notification_callbacks_are_source_scoped():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        key = (
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            "0000180f-0000-1000-8000-00805f9b34fb",
            "00002a19-0000-1000-8000-00805f9b34fb",
        )
        updates = []

        def callback(characteristic):
            updates.append(characteristic.value)

        runtime._notification_callbacks[key] = [callback]
        runtime.stats.active_notifications_enabled = 1

        for source, value in (
            ("02:00:00:00:00:02", b"\x65"),
            ("02:00:00:00:00:01", b"\x66"),
        ):
            await runtime._async_handle_message(
                ArubaTelemetryMessage(
                    reporter=_reporter(source),
                    events=[],
                    action_results=[],
                    characteristics=[
                        ArubaCharacteristic(
                            reporter=_reporter(source),
                            device_mac="02:00:00:00:01:01",
                            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                            characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                            value=value,
                            description="Battery Level",
                            properties=("notify",),
                        )
                    ],
                )
            )

        assert updates == [b"\x66"]
        assert runtime.stats.active_notification_updates == 1

    asyncio.run(run_test())


def test_runtime_stop_notify_keeps_callback_when_disable_fails():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        def callback(characteristic):
            return None

        key = (
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            "0000180f-0000-1000-8000-00805f9b34fb",
            "00002a19-0000-1000-8000-00805f9b34fb",
        )
        runtime._notification_callbacks[key] = [callback]
        runtime.stats.active_notifications_enabled = 1

        stop_task = asyncio.create_task(
            runtime.async_stop_gatt_notify(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                callback=callback,
            )
        )
        await asyncio.sleep(0)
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type=ACTION_GATT_NOTIFICATION,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.GATT_ERROR,
                        status_name="gattError",
                        status_string="failed",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        response = await stop_task
        assert response["result"]["status"] == "gattError"
        assert runtime._notification_callbacks[key] == [callback]
        assert runtime.stats.active_notifications_enabled == 1
        assert runtime.stats.active_action_failures == 1
        assert runtime.stats.last_active_action_error == "gattError: failed"

    asyncio.run(run_test())


def test_runtime_tracks_action_result_timeout_diagnostics(monkeypatch):
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        async def raise_timeout(future, timeout):
            raise TimeoutError

        monkeypatch.setattr(asyncio, "wait_for", raise_timeout)

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        response = await runtime.async_send_aruba_action(
            ap_mac="02:00:00:00:00:01",
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                action_id="connect-timeout",
                device_mac="02:00:00:00:01:01",
            ),
        )

        assert response["result"]["received"] is False
        assert response["result"]["status"] == "timeout_waiting_for_action_result"
        assert runtime.stats.active_action_timeouts == 1
        assert runtime.stats.last_active_action_status == "timeout_waiting_for_action_result"
        assert runtime.stats.last_active_action_error == "timeout_waiting_for_action_result"
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_cleans_pending_action_when_cancelled():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-cancel",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert "connect-cancel" in runtime._pending_actions

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert runtime._pending_actions == {}
        assert runtime.stats.active_action_cancellations == 1
        assert runtime.stats.last_active_action_status == "cancelled_waiting_for_action_result"
        assert runtime.stats.last_active_action_error == "cancelled_waiting_for_action_result"
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_tracks_late_success_result_without_clearing_timeout_error():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime.stats.active_action_timeouts = 1
        runtime.stats.last_active_action_status = "timeout_waiting_for_action_result"
        runtime.stats.last_active_action_error = "timeout_waiting_for_action_result"

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="late-success",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        assert runtime.stats.active_action_results == 1
        assert runtime.stats.active_action_orphan_results == 1
        assert runtime.stats.last_active_action_id == "late-success"
        assert runtime.stats.last_active_action_type == ACTION_BLE_CONNECT
        assert runtime.stats.last_active_action_status == "success"
        assert runtime.stats.last_active_action_error == "timeout_waiting_for_action_result"

    asyncio.run(run_test())


def test_runtime_tracks_orphan_failure_result_as_failure():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="orphan-failure",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.ACTION_TIMEOUT,
                        status_name="actionTimeout",
                        status_string="late failure",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        assert runtime.stats.active_action_results == 1
        assert runtime.stats.active_action_orphan_results == 1
        assert runtime.stats.active_action_failures == 1
        assert runtime.stats.last_active_action_type == ACTION_BLE_CONNECT
        assert runtime.stats.last_active_action_error == "actionTimeout: late failure"

    asyncio.run(run_test())


def test_runtime_tracks_device_disconnect_status_and_forgets_notifications():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        key = (
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            "0000180f-0000-1000-8000-00805f9b34fb",
            "00002a19-0000-1000-8000-00805f9b34fb",
        )

        def callback(characteristic):
            return None

        runtime._notification_callbacks[key] = [callback]
        runtime.stats.active_notifications_enabled = 1

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=1,
                        status_name="inactivityTimeout",
                        status_string="idle timeout",
                        mtu=None,
                    )
                ],
            )
        )

        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_status_updates"] == 1
        assert diagnostics["active_disconnect_statuses"] == 1
        assert diagnostics["last_active_status_source"] == "02:00:00:00:00:01"
        assert diagnostics["last_active_status_device"] == "02:00:00:00:01:01"
        assert diagnostics["last_active_status"] == "inactivityTimeout"
        assert diagnostics["last_active_status_string"] == "idle timeout"
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False
        assert runtime._notification_callbacks == {}
        assert runtime.stats.active_notifications_enabled == 0

    asyncio.run(run_test())


def test_runtime_notifies_device_disconnect_listeners_and_unsubscribes():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        updates = []

        unsubscribe = runtime.add_device_disconnect_listener(
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            updates.append,
        )

        status = ArubaStatusUpdate(
            reporter=_event().reporter,
            device_mac="02:00:00:00:01:01",
            status=0,
            status_name="deviceDisconnected",
            status_string="lost",
            mtu=None,
        )
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[status],
            )
        )

        assert updates == [status]

        unsubscribe()
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[status],
            )
        )

        assert updates == [status]

    asyncio.run(run_test())


def test_runtime_device_disconnect_resolves_device_characteristic_waiters():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        task = asyncio.create_task(
            runtime.async_wait_for_device_characteristics(
                "02:00:00:00:01:01",
                timeout=20,
            )
        )
        await asyncio.sleep(0)
        assert (None, "02:00:00:00:01:01") in runtime._pending_device_characteristics

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string="lost during discovery",
                        mtu=None,
                    )
                ],
            )
        )

        assert await task == []
        assert runtime._pending_device_characteristics == {}

    asyncio.run(run_test())


def test_runtime_successful_disconnect_action_notifies_device_listeners():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        updates = []
        runtime.add_device_disconnect_listener(
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            updates.append,
        )
        future = asyncio.get_running_loop().create_future()
        runtime._pending_actions["disconnect-1"] = future

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="disconnect-1",
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )

        assert len(updates) == 1
        assert updates[0].status_name == "deviceDisconnected"
        assert updates[0].status_string == "ok"
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False

    asyncio.run(run_test())


def test_runtime_device_disconnect_status_completes_pending_disconnect_action():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_DISCONNECT,
                    action_id="disconnect-device-lost",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string="disconnected",
                        mtu=None,
                    )
                ],
            )
        )

        response = await task
        assert response["result"]["status"] == "deviceDisconnected"
        assert runtime.stats.active_action_failures == 0
        assert runtime.stats.last_active_action_error is None
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}

    asyncio.run(run_test())


def test_runtime_source_disconnect_marks_active_devices_disconnected():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        updates = []
        runtime.add_device_disconnect_listener(
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
            updates.append,
        )
        future = asyncio.get_running_loop().create_future()
        runtime._pending_actions["connect-1"] = future

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id="connect-1",
                        action_type=ACTION_BLE_CONNECT,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is True

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_source_disconnects"] == 1
        assert diagnostics["active_disconnect_statuses"] == 1
        assert diagnostics["last_active_status_source"] == "02:00:00:00:00:01"
        assert diagnostics["last_active_status_device"] == "02:00:00:00:01:01"
        assert diagnostics["last_active_status"] == "sourceDisconnected"
        assert diagnostics["active_connected_devices"] == []
        assert diagnostics["active_disconnected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "status": "sourceDisconnected",
            }
        ]
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False
        assert len(updates) == 1
        assert updates[0].status_name == "sourceDisconnected"

    asyncio.run(run_test())


def test_runtime_source_disconnect_fails_pending_action_immediately():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-source-lost",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert "connect-source-lost" in runtime._pending_actions
        assert "connect-source-lost" in runtime._pending_action_contexts

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        response = await task
        assert response["result"]["received"] is True
        assert response["result"]["status"] == "sourceDisconnected"
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}
        assert runtime.stats.active_action_failures == 1
        assert runtime.stats.last_active_action_error == (
            "sourceDisconnected: Aruba WebSocket source disconnected"
        )
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_source_disconnect_completes_pending_disconnect_action():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_DISCONNECT,
                    action_id="disconnect-source-lost",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)
        assert "disconnect-source-lost" in runtime._pending_actions

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        response = await task
        assert response["result"]["received"] is True
        assert response["result"]["status"] == "sourceDisconnected"
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}
        assert runtime.stats.active_action_failures == 0
        assert runtime.stats.last_active_action_error is None
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_gatt_read_does_not_wait_for_characteristic_after_source_disconnect():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=20,
            )
        )
        await asyncio.sleep(0)
        assert runtime._pending_actions
        assert runtime._pending_characteristics

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        response = await task
        assert response["result"]["status"] == "sourceDisconnected"
        assert "characteristic" not in response
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}
        assert runtime._pending_characteristics == {}
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_device_disconnect_fails_pending_action_immediately():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_send_aruba_action(
                ap_mac="02:00:00:00:00:01",
                request=ArubaBleActionRequest(
                    action_type=ACTION_BLE_CONNECT,
                    action_id="connect-device-lost",
                    device_mac="02:00:00:00:01:01",
                ),
            )
        )
        await asyncio.sleep(0)

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string="lost during connect",
                        mtu=None,
                    )
                ],
            )
        )

        response = await task
        assert response["result"]["received"] is True
        assert response["result"]["status"] == "deviceDisconnected"
        assert response["result"]["status_string"] == "lost during connect"
        assert runtime._pending_actions == {}
        assert runtime._pending_action_contexts == {}
        assert runtime.stats.active_action_failures == 1
        assert runtime.stats.last_active_action_error == (
            "deviceDisconnected: lost during connect"
        )

    asyncio.run(run_test())


def test_runtime_gatt_read_waiting_for_value_stops_after_device_disconnect():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=20,
            )
        )
        await asyncio.sleep(0)
        action_id = runtime.stats.last_active_action_id or ""

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=action_id,
                        action_type="gattRead",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        await asyncio.sleep(0)
        assert runtime._pending_characteristics

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string="lost before value",
                        mtu=None,
                    )
                ],
            )
        )

        response = await task
        assert response["result"]["status"] == "success"
        assert response["characteristic"] == {
            "received": False,
            "status": "deviceDisconnected",
            "status_string": "lost before value",
        }
        assert runtime._pending_characteristics == {}

    asyncio.run(run_test())


def test_runtime_gatt_read_waiting_for_value_stops_after_source_disconnect():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=20,
            )
        )
        await asyncio.sleep(0)
        action_id = runtime.stats.last_active_action_id or ""

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=action_id,
                        action_type="gattRead",
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        await asyncio.sleep(0)
        assert runtime._pending_characteristics

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        response = await task
        assert response["result"]["status"] == "success"
        assert response["characteristic"] == {
            "received": False,
            "status": "sourceDisconnected",
            "status_string": "Aruba WebSocket source disconnected",
        }
        assert runtime._pending_characteristics == {}
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_disconnected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "status": "sourceDisconnected",
            }
        ]

    asyncio.run(run_test())


def test_runtime_source_disconnect_resolves_source_characteristic_waiters():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        wait_task = asyncio.create_task(
            runtime.async_wait_for_device_characteristics(
                "02:00:00:00:01:01",
                source="02:00:00:00:00:01",
                timeout=20,
            )
        )
        await asyncio.sleep(0)
        assert (
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
        ) in runtime._pending_device_characteristics

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        assert await wait_task == []
        assert runtime._pending_device_characteristics == {}

    asyncio.run(run_test())


def test_runtime_forgets_characteristics_after_device_disconnect():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
                statuses=[],
            )
        )
        assert len(runtime.characteristics_for_device("02:00:00:00:01:01")) == 1

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string="gone",
                        mtu=None,
                    )
                ],
            )
        )

        assert runtime.characteristics_for_device("02:00:00:00:01:01") == []

    asyncio.run(run_test())


def test_runtime_clear_device_characteristics_is_source_scoped():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        for reporter in (
            _reporter("02:00:00:00:00:01"),
            _reporter("02:00:00:00:00:02"),
        ):
            await runtime._async_handle_message(
                ArubaTelemetryMessage(
                    reporter=reporter,
                    events=[],
                    action_results=[],
                    characteristics=[
                        ArubaCharacteristic(
                            reporter=reporter,
                            device_mac="02:00:00:00:01:01",
                            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                            characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                            value=b"\x64",
                            description="Battery Level",
                            properties=("read",),
                        )
                    ],
                    statuses=[],
                )
            )

        assert len(runtime.characteristics_for_device("02:00:00:00:01:01")) == 2

        assert runtime.clear_device_characteristics(
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
        ) is True

        assert runtime.characteristics_for_device(
            "02:00:00:00:01:01",
            source="02:00:00:00:00:01",
        ) == []
        assert len(
            runtime.characteristics_for_device(
                "02:00:00:00:01:01",
                source="02:00:00:00:00:02",
            )
        ) == 1
        assert runtime.clear_device_characteristics(
            "02:00:00:00:00:01",
            "02:00:00:00:01:01",
        ) is False

    asyncio.run(run_test())


def test_runtime_source_disconnect_forgets_cached_characteristics():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
                statuses=[],
            )
        )
        assert len(runtime.characteristics_for_device("02:00:00:00:01:01")) == 1

        runtime._handle_source_disconnect("02:00:00:00:00:01")

        assert runtime.characteristics_for_device("02:00:00:00:01:01") == []
        assert runtime.diagnostic_attributes()["active_disconnected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "status": "sourceDisconnected",
            }
        ]

    asyncio.run(run_test())


def test_runtime_connection_update_clears_stale_disconnect_status():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string=None,
                        mtu=None,
                    )
                ],
            )
        )
        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is False

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=2,
                        status_name="connectionUpdate",
                        status_string=None,
                        mtu=185,
                    )
                ],
            )
        )

        assert runtime.is_device_active("02:00:00:00:00:01", "02:00:00:00:01:01") is True
        assert runtime.stats.last_active_mtu == 185
        assert runtime.mtu_for_device("02:00:00:00:00:01", "02:00:00:00:01:01") == 185
        diagnostics = runtime.diagnostic_attributes()
        assert diagnostics["active_connected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
            }
        ]
        assert diagnostics["active_device_mtu"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "mtu": 185,
            }
        ]

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="02:00:00:00:01:01",
                        status=0,
                        status_name="deviceDisconnected",
                        status_string=None,
                        mtu=None,
                    )
                ],
            )
        )
        assert runtime.mtu_for_device("02:00:00:00:00:01", "02:00:00:00:01:01") is None

    asyncio.run(run_test())


def test_runtime_stop_sends_best_effort_disconnect_for_active_devices():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver
        updates = []
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}
        runtime.add_device_disconnect_listener(key[0], key[1], updates.append)

        await runtime.async_stop()

        assert len(receiver.payloads) == 1
        assert receiver.payloads[0][0] == "02:00:00:00:00:01"
        assert runtime._active_device_keys_by_source == {}
        assert runtime.is_device_active(key[0], key[1]) is False
        assert runtime.stats.active_actions_sent == 1
        assert runtime.stats.active_disconnect_statuses == 1
        assert len(updates) == 1
        assert updates[0].status_name == "deviceDisconnected"
        assert updates[0].status_string == "Aruba runtime stopped"

    asyncio.run(run_test())


def test_runtime_stop_does_not_wait_behind_active_operation_lock():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver
        key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
        runtime._active_device_keys_by_source[key[0]] = {key}

        read_task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac=key[0],
                device_mac=key[1],
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                timeout=300,
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 1
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 1

        await runtime.async_stop()

        assert len(receiver.payloads) == 2
        assert runtime._active_device_keys_by_source == {}
        response = await read_task
        assert response["result"]["status"] == "deviceDisconnected"
        assert response["result"]["status_string"] == "Aruba runtime stopped"
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_cleans_gatt_read_waiters_when_cancelled():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        runtime._receiver = Receiver()

        task = asyncio.create_task(
            runtime.async_gatt_read(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
            )
        )
        await asyncio.sleep(0)
        assert runtime._pending_actions
        assert runtime._pending_characteristics

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert runtime._pending_actions == {}
        assert runtime._pending_characteristics == {}
        assert runtime.stats.active_action_cancellations == 1
        assert runtime.diagnostic_attributes()["active_operation_locks"] == 0

    asyncio.run(run_test())


def test_runtime_notify_reference_counts_callbacks():
    async def run_test():
        class Receiver:
            def __init__(self):
                self.payloads = []
                self.stats = type(
                    "Stats",
                    (),
                    {
                        "connections_opened": 0,
                        "connections_closed": 0,
                        "binary_messages": 0,
                        "text_messages": 0,
                        "invalid_tokens": 0,
                        "decode_errors": 0,
                        "last_peer": None,
                    },
                )()

            async def async_send_to_source(self, source, payload):
                self.payloads.append((source, payload))

            def connected_sources(self):
                return ["02:00:00:00:00:01"]

        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )
        receiver = Receiver()
        runtime._receiver = receiver

        def callback_one(characteristic):
            return None

        def callback_two(characteristic):
            return None

        start_task = asyncio.create_task(
            runtime.async_start_gatt_notify(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                callback=callback_one,
            )
        )
        await asyncio.sleep(0)
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type=ACTION_GATT_NOTIFICATION,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        await start_task

        second_response = await runtime.async_start_gatt_notify(
            ap_mac="02:00:00:00:00:01",
            device_mac="02:00:00:00:01:01",
            service_uuid="180f",
            characteristic_uuid="2a19",
            callback=callback_two,
        )
        assert second_response["sent"] is False
        assert second_response["status"] == "already_enabled"
        assert second_response["service_uuid"] == "0000180f-0000-1000-8000-00805f9b34fb"
        assert second_response["characteristic_uuid"] == (
            "00002a19-0000-1000-8000-00805f9b34fb"
        )
        assert len(receiver.payloads) == 1
        assert runtime.stats.active_notifications_enabled == 2

        first_stop = await runtime.async_stop_gatt_notify(
            ap_mac="02:00:00:00:00:01",
            device_mac="02:00:00:00:01:01",
            service_uuid="180f",
            characteristic_uuid="2a19",
            callback=callback_one,
        )
        assert first_stop["sent"] is False
        assert first_stop["status"] == "callbacks_remaining"
        assert first_stop["service_uuid"] == "0000180f-0000-1000-8000-00805f9b34fb"
        assert first_stop["characteristic_uuid"] == (
            "00002a19-0000-1000-8000-00805f9b34fb"
        )
        assert len(receiver.payloads) == 1
        assert runtime.stats.active_notifications_enabled == 1

        final_stop_task = asyncio.create_task(
            runtime.async_stop_gatt_notify(
                ap_mac="02:00:00:00:00:01",
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                callback=callback_two,
            )
        )
        await asyncio.sleep(0)
        assert len(receiver.payloads) == 2
        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[
                    ArubaActionResult(
                        reporter=_event().reporter,
                        action_id=runtime.stats.last_active_action_id or "",
                        action_type=ACTION_GATT_NOTIFICATION,
                        device_mac="02:00:00:00:01:01",
                        status=ArubaActionStatus.SUCCESS,
                        status_name="success",
                        status_string="ok",
                        apb_mac=None,
                    )
                ],
                characteristics=[],
            )
        )
        final_stop = await final_stop_task
        assert final_stop["result"]["status"] == "success"
        assert runtime.stats.active_notifications_enabled == 0

    asyncio.run(run_test())


def test_runtime_forgets_notification_callback_locally():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )
    key = (
        "02:00:00:00:00:01",
        "02:00:00:00:01:01",
        "0000180f-0000-1000-8000-00805f9b34fb",
        "00002a19-0000-1000-8000-00805f9b34fb",
    )

    def callback(characteristic):
        return None

    runtime._notification_callbacks[key] = [callback]
    runtime.stats.active_notifications_enabled = 1

    removed = runtime.forget_gatt_notify_callback(
        device_mac="02:00:00:00:01:01",
        service_uuid="180f",
        characteristic_uuid="2a19",
        callback=callback,
    )

    assert removed is True
    assert key not in runtime._notification_callbacks
    assert runtime.stats.active_notifications_enabled == 0


def test_runtime_exposes_active_ble_enabled_diagnostic():
    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
        enable_active_ble=False,
    )

    diagnostics = runtime.diagnostic_attributes()

    assert diagnostics["active_ble_enabled"] is False
    assert diagnostics["active_action_failures"] == 0
    assert diagnostics["active_action_timeouts"] == 0
    assert diagnostics["active_action_cancellations"] == 0
    assert diagnostics["active_action_orphan_results"] == 0
    assert diagnostics["last_active_action_type"] is None
    assert diagnostics["last_active_action_duration_ms"] is None
    assert diagnostics["slowest_active_action_type"] is None
    assert diagnostics["slowest_active_action_status"] is None
    assert diagnostics["slowest_active_action_duration_ms"] is None
    assert diagnostics["active_action_duration_total_ms"] == 0
    assert diagnostics["last_active_characteristic_wait_status"] is None
    assert diagnostics["last_active_characteristic_wait_duration_ms"] is None
    assert diagnostics["slowest_active_characteristic_wait_status"] is None
    assert diagnostics["slowest_active_characteristic_wait_duration_ms"] is None
    assert diagnostics["active_characteristic_wait_duration_total_ms"] == 0
    assert diagnostics["active_status_updates"] == 0
    assert diagnostics["active_disconnect_statuses"] == 0
    assert diagnostics["active_source_disconnects"] == 0
    assert diagnostics["active_operation_locks"] == 0
    assert diagnostics["active_operations_in_flight"] == 0
    assert diagnostics["active_operations_waiting"] == 0
    assert diagnostics["active_connected_devices"] == []
    assert diagnostics["active_disconnected_devices"] == []
    assert diagnostics["active_device_mtu"] == []
    assert diagnostics["active_pending_actions"] == []
    assert diagnostics["active_pending_characteristic_reads"] == []
    assert diagnostics["active_pending_device_discoveries"] == []
    assert diagnostics["active_notification_subscriptions"] == []


def test_runtime_normalizes_mac_addresses_across_active_state():
    async def run_test():
        runtime = ArubaBleProxyRuntime(
            hass=None,
            host="0.0.0.0",
            port=7443,
            access_token="secret",
        )

        await runtime._async_handle_message(
            ArubaTelemetryMessage(
                reporter=_event().reporter,
                events=[],
                action_results=[],
                characteristics=[
                    ArubaCharacteristic(
                        reporter=_event().reporter,
                        device_mac="02-00-00-00-01-01",
                        service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        value=b"\x64",
                        description="Battery Level",
                        properties=("read",),
                    )
                ],
                statuses=[
                    ArubaStatusUpdate(
                        reporter=_event().reporter,
                        device_mac="020000000101",
                        status=2,
                        status_name="connectionUpdate",
                        status_string="connected",
                        mtu=185,
                    )
                ],
            )
        )

        assert runtime.is_device_active("020000000001", "020000000101") is True
        assert runtime.mtu_for_device("02-00-00-00-00-01", "020000000101") == 185
        assert len(runtime.characteristics_for_device("020000000101")) == 1
        assert runtime.diagnostic_attributes()["active_connected_devices"] == [
            {
                "source": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
            }
        ]

    asyncio.run(run_test())


def test_runtime_normalizes_sources_for_connected_lookup_and_disconnect():
    class Receiver:
        stats = type(
            "Stats",
            (),
            {
                "connections_opened": 0,
                "connections_closed": 0,
                "binary_messages": 0,
                "text_messages": 0,
                "invalid_tokens": 0,
                "decode_errors": 0,
                "last_peer": None,
            },
        )()

        def connected_sources(self):
            return ["02:00:00:00:00:01"]

    runtime = ArubaBleProxyRuntime(
        hass=None,
        host="0.0.0.0",
        port=7443,
        access_token="secret",
    )
    runtime._receiver = Receiver()
    assert runtime.can_connect_source("020000000001") is True

    key = ("02:00:00:00:00:01", "02:00:00:00:01:01")
    runtime._active_device_keys_by_source[key[0]] = {key}
    updates = []
    runtime.add_device_disconnect_listener("020000000001", "020000000101", updates.append)

    assert runtime.can_connect_source("020000000001") is False
    assert runtime.active_devices_for_source("020000000001") == ["02:00:00:00:01:01"]

    runtime._handle_source_disconnect("020000000001")

    assert len(updates) == 1
    assert runtime.is_device_active("02:00:00:00:00:01", "02-00-00-00-01-01") is False
    assert runtime.diagnostic_attributes()["active_disconnected_devices"] == [
        {
            "source": "02:00:00:00:00:01",
            "device_mac": "02:00:00:00:01:01",
            "status": "sourceDisconnected",
        }
    ]
