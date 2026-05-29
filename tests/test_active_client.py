import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

from custom_components.aruba_ble_proxy.active import ACTION_BLE_DISCONNECT
from custom_components.aruba_ble_proxy.active_client import (
    SWITCHBOT_READ_CHAR_UUID,
    SWITCHBOT_WRITE_CHAR_UUID,
    build_service_collection,
    create_aruba_bleak_client,
)
from custom_components.aruba_ble_proxy.models import ArubaCharacteristic, Reporter


def _install_fake_bleak(monkeypatch):
    class BleakError(Exception):
        pass

    class BaseBleakClient:
        def __init__(self, address_or_ble_device, **kwargs):
            self.address = address_or_ble_device
            self._timeout = kwargs.get("timeout", 10.0)
            self._disconnected_callback = kwargs.get("disconnected_callback")

    class BleakGATTServiceCollection:
        pass

    class BleakGATTCharacteristic:
        pass

    class BleakGATTService:
        pass

    modules = {
        "bleak": types.ModuleType("bleak"),
        "bleak.backends": types.ModuleType("bleak.backends"),
        "bleak.backends.client": types.ModuleType("bleak.backends.client"),
        "bleak.backends.service": types.ModuleType("bleak.backends.service"),
        "bleak.exc": types.ModuleType("bleak.exc"),
    }
    modules["bleak.backends.client"].BaseBleakClient = BaseBleakClient
    modules["bleak.backends.service"].BleakGATTServiceCollection = (
        BleakGATTServiceCollection
    )
    modules["bleak.backends.characteristic"] = types.ModuleType(
        "bleak.backends.characteristic"
    )
    modules["bleak.backends.characteristic"].BleakGATTCharacteristic = (
        BleakGATTCharacteristic
    )
    modules["bleak.backends.service"].BleakGATTService = BleakGATTService
    modules["bleak.exc"].BleakError = BleakError

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    return BleakError


def _install_fake_bleak_services(monkeypatch):
    class BleakError(Exception):
        pass

    class BaseBleakClient:
        def __init__(self, address_or_ble_device, **kwargs):
            self.address = address_or_ble_device
            self._timeout = kwargs.get("timeout", 10.0)
            self._disconnected_callback = kwargs.get("disconnected_callback")

    class BleakGATTService:
        def __init__(self, *, obj, handle, uuid):
            self.obj = obj
            self.handle = handle
            self.uuid = uuid
            self.characteristics = []

    class BleakGATTCharacteristic:
        def __init__(
            self,
            *,
            obj,
            handle,
            uuid,
            properties,
            max_write_without_response_size,
            service,
        ):
            self.obj = obj
            self.handle = handle
            self.uuid = uuid
            self.properties = properties
            self.max_write_without_response_size = max_write_without_response_size
            self.service_uuid = service.uuid
            self.service_handle = service.handle

    class BleakGATTServiceCollection:
        def __init__(self):
            self.services = {}
            self.characteristics = {}

        def add_service(self, service):
            self.services[service.uuid] = service

        def get_service(self, specifier):
            return self.services.get(specifier)

        def add_characteristic(self, characteristic):
            self.characteristics[characteristic.uuid] = characteristic
            self.services[characteristic.service_uuid].characteristics.append(characteristic)

        def get_characteristic(self, specifier):
            for characteristic in self.characteristics.values():
                if specifier in (characteristic.uuid, characteristic.handle):
                    return characteristic
            return None

    modules = {
        "bleak": types.ModuleType("bleak"),
        "bleak.backends": types.ModuleType("bleak.backends"),
        "bleak.backends.client": types.ModuleType("bleak.backends.client"),
        "bleak.backends.characteristic": types.ModuleType(
            "bleak.backends.characteristic"
        ),
        "bleak.backends.service": types.ModuleType("bleak.backends.service"),
        "bleak.exc": types.ModuleType("bleak.exc"),
    }
    modules["bleak.backends.client"].BaseBleakClient = BaseBleakClient
    modules["bleak.backends.characteristic"].BleakGATTCharacteristic = (
        BleakGATTCharacteristic
    )
    modules["bleak.backends.service"].BleakGATTService = BleakGATTService
    modules["bleak.backends.service"].BleakGATTServiceCollection = (
        BleakGATTServiceCollection
    )
    modules["bleak.exc"].BleakError = BleakError

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


class _FakeServiceCollection:
    def __init__(self, *characteristics):
        self._characteristics = list(characteristics)

    def get_characteristic(self, specifier):
        for characteristic in self._characteristics:
            if specifier in (characteristic.uuid, getattr(characteristic, "handle", None)):
                return characteristic
        return None


def test_build_service_collection_groups_characteristics_by_service(monkeypatch):
    _install_fake_bleak_services(monkeypatch)
    reporter = Reporter(
        name=None,
        mac="02:00:00:00:00:01",
        ipv4=None,
        ipv6=None,
        hardware_type=None,
        software_version=None,
        software_build=None,
        timestamp=None,
    )

    services = build_service_collection(
        [
            ArubaCharacteristic(
                reporter=reporter,
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                value=b"\x64",
                description="Battery Level",
                properties=("read", "notify"),
            ),
            ArubaCharacteristic(
                reporter=reporter,
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a1a-0000-1000-8000-00805f9b34fb",
                value=b"\x01",
                description=None,
                properties=("writeWithoutResponse",),
            ),
            ArubaCharacteristic(
                reporter=reporter,
                device_mac="02:00:00:00:01:01",
                service_uuid=None,
                characteristic_uuid="00002a1b-0000-1000-8000-00805f9b34fb",
                value=b"",
                description=None,
                properties=(),
            ),
        ]
    )

    service = services.get_service("0000180f-0000-1000-8000-00805f9b34fb")
    battery = services.get_characteristic("00002a19-0000-1000-8000-00805f9b34fb")
    writable = services.get_characteristic("00002a1a-0000-1000-8000-00805f9b34fb")

    assert len(services.services) == 1
    assert service is not None
    assert [char.uuid for char in service.characteristics] == [
        "00002a19-0000-1000-8000-00805f9b34fb",
        "00002a1a-0000-1000-8000-00805f9b34fb",
    ]
    assert battery.handle == 2
    assert battery.service_uuid == service.uuid
    assert battery.properties == ["read", "notify"]
    assert battery.max_write_without_response_size() == 20
    assert writable.handle == 3
    assert writable.properties == ["write-without-response"]


def test_build_service_collection_adds_switchbot_fallback_from_advertisement(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    services = build_service_collection(
        [],
        advertisement_service_uuids={"fd3d"},
    )

    read_char = services.get_characteristic(SWITCHBOT_READ_CHAR_UUID)
    write_char = services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID)

    assert read_char is not None
    assert read_char.properties == ["notify", "read"]
    assert write_char is not None
    assert write_char.properties == ["write-without-response"]


def test_build_service_collection_does_not_add_switchbot_fallback_without_advertisement(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    services = build_service_collection([])

    assert services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is None
    assert services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID) is None


def test_build_service_collection_adds_only_missing_switchbot_fallback_characteristic(monkeypatch):
    _install_fake_bleak_services(monkeypatch)
    reporter = Reporter(
        name=None,
        mac="02:00:00:00:00:01",
        ipv4=None,
        ipv6=None,
        hardware_type=None,
        software_version=None,
        software_build=None,
        timestamp=None,
    )

    services = build_service_collection(
        [
            ArubaCharacteristic(
                reporter=reporter,
                device_mac="02:00:00:00:01:01",
                service_uuid="cba20d00-224d-11e6-9fb8-0002a5d5c51b",
                characteristic_uuid=SWITCHBOT_READ_CHAR_UUID,
                value=b"",
                description=None,
                properties=("notify",),
            )
        ],
        advertisement_service_uuids={"fd3d"},
    )

    assert services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None
    assert services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID) is not None
    assert len(services.get_service("cba20d00-224d-11e6-9fb8-0002a5d5c51b").characteristics) == 2


def test_aruba_bleak_client_disconnect_forgets_registered_notifications(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []
            self.starts = []
            self.forgotten = []

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append((ap_mac, request))
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_start_gatt_notify(self, **kwargs):
            self.starts.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        await client.start_notify(characteristic, lambda *_: None)
        assert client._notify_callbacks

        await client.disconnect()

        assert client.is_connected is False
        assert client._notify_callbacks == {}
        assert runtime.actions[-1][1].action_type == ACTION_BLE_DISCONNECT
        assert runtime.forgotten == [
            {
                "ap_mac": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "callback": runtime.starts[0]["callback"],
            }
        ]

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_accepts_source_disconnected(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append((ap_mac, request, wait_result))
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "sourceDisconnected",
                    "status_string": "Aruba WebSocket source disconnected",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        client._is_connected = True

        assert await client.disconnect() is True

        assert client.is_connected is False
        assert runtime.actions[-1][1].action_type == ACTION_BLE_DISCONNECT

    asyncio.run(run_test())


def test_aruba_bleak_client_requested_disconnect_suppresses_callback(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.listener = None

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listener = listener
            return lambda: None

        def is_device_active(self, source, address):
            return True

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            if request.action_type == ACTION_BLE_DISCONNECT and self.listener is not None:
                self.listener(object())
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

    async def run_test():
        disconnected = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls(
            "02:00:00:00:01:01",
            disconnected_callback=lambda closed_client: disconnected.append(closed_client),
        )

        assert await client.connect() is True
        assert await client.disconnect() is True

        assert client.is_connected is False
        assert disconnected == []

    asyncio.run(run_test())


def test_aruba_bleak_client_read_accepts_characteristic_uuid(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.reads = []

        async def async_gatt_read(self, **kwargs):
            self.reads.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
                "characteristic": {
                    "value": "0102",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            handle=12,
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        value = await client.read_gatt_char(characteristic.uuid)

        assert value == bytearray([1, 2])
        assert runtime.reads == [
            {
                "ap_mac": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "timeout": 10,
                "wait_result": True,
            }
        ]

    asyncio.run(run_test())


def test_aruba_bleak_client_read_accepts_short_characteristic_uuid(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.reads = []

        async def async_gatt_read(self, **kwargs):
            self.reads.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
                "characteristic": {
                    "value": "64",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            handle=12,
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        value = await client.read_gatt_char("2A19")

        assert value == bytearray([100])
        assert runtime.reads[-1]["service_uuid"] == characteristic.service_uuid
        assert runtime.reads[-1]["characteristic_uuid"] == characteristic.uuid

    asyncio.run(run_test())


def test_aruba_bleak_client_read_reports_aruba_action_status_string(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        async def async_gatt_read(self, **kwargs):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "deviceDisconnected",
                    "status_string": "Device disconnected before read completed",
                },
            }

    async def run_test():
        client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )
        client._is_connected = True

        try:
            await client.read_gatt_char(characteristic)
        except BleakError as err:
            assert "deviceDisconnected" in str(err)
            assert "Device disconnected before read completed" in str(err)
        else:
            raise AssertionError("read should fail when Aruba reports a failed status")

    asyncio.run(run_test())


def test_aruba_bleak_client_read_reports_characteristic_status_string(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        async def async_gatt_read(self, **kwargs):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
                "characteristic": {
                    "received": False,
                    "status": "inactivityTimeout",
                    "status_string": "Timed out waiting for characteristic value",
                },
            }

    async def run_test():
        client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )
        client._is_connected = True

        try:
            await client.read_gatt_char(characteristic)
        except BleakError as err:
            assert "did not return a characteristic value" in str(err)
            assert "inactivityTimeout" in str(err)
            assert "Timed out waiting for characteristic value" in str(err)
        else:
            raise AssertionError("read should fail when characteristic value is missing")

    asyncio.run(run_test())


def test_aruba_bleak_client_read_rejects_unknown_characteristic_uuid(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        async def async_gatt_read(self, **kwargs):
            raise AssertionError("read should not be attempted for unknown characteristic")

    async def run_test():
        client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        client._is_connected = True
        client.services = _FakeServiceCollection()

        try:
            await client.read_gatt_char("00002a19-0000-1000-8000-00805f9b34fb")
        except BleakError as err:
            assert "characteristic not found" in str(err)
        else:
            raise AssertionError("read should fail for unknown characteristic")

    asyncio.run(run_test())


def test_aruba_bleak_client_write_accepts_handle_and_infers_no_response(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.writes = []

        async def async_gatt_write(self, **kwargs):
            self.writes.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            handle=7,
            properties=["write-without-response"],
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        await client.write_gatt_char(7, b"\x01", timeout=42)

        assert runtime.writes[-1]["characteristic_uuid"] == characteristic.uuid
        assert runtime.writes[-1]["service_uuid"] == characteristic.service_uuid
        assert runtime.writes[-1]["value"] == b"\x01"
        assert runtime.writes[-1]["with_response"] is False
        assert runtime.writes[-1]["wait_result"] is False
        assert runtime.writes[-1]["timeout"] == 42

    asyncio.run(run_test())


def test_aruba_bleak_client_write_prefers_response_property(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.writes = []

        async def async_gatt_write(self, **kwargs):
            self.writes.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            handle=8,
            properties=["write", "write-without-response"],
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        await client.write_gatt_char(characteristic.uuid, b"\x01")

        assert runtime.writes[-1]["with_response"] is True
        assert runtime.writes[-1]["wait_result"] is True

    asyncio.run(run_test())


def test_aruba_bleak_client_notify_accepts_characteristic_uuid(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.started = []
            self.stopped = []

        async def async_start_gatt_notify(self, **kwargs):
            self.started.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_stop_gatt_notify(self, **kwargs):
            self.stopped.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        values = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            handle=9,
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        await client.start_notify(
            characteristic.uuid,
            lambda sender, data: values.append((sender, data)),
        )
        runtime.started[-1]["callback"](SimpleNamespace(value=b"\x02"))
        await client.stop_notify(characteristic.uuid, timeout=43)

        assert runtime.started[-1]["characteristic_uuid"] == characteristic.uuid
        assert runtime.started[-1]["service_uuid"] == characteristic.service_uuid
        assert values == [(characteristic, bytearray([2]))]
        assert runtime.stopped[-1]["characteristic_uuid"] == characteristic.uuid
        assert runtime.stopped[-1]["service_uuid"] == characteristic.service_uuid
        assert runtime.stopped[-1]["timeout"] == 43

    asyncio.run(run_test())


def test_aruba_bleak_client_notify_normalizes_characteristic_uuid(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.started = []
            self.stopped = []

        async def async_start_gatt_notify(self, **kwargs):
            self.started.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_stop_gatt_notify(self, **kwargs):
            self.stopped.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="180F",
            uuid="2A19",
        )

        client._is_connected = True
        await client.start_notify(characteristic, lambda *_: None)
        await client.stop_notify(
            SimpleNamespace(
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                uuid="00002a19-0000-1000-8000-00805f9b34fb",
            )
        )

        assert runtime.started[-1]["service_uuid"] == (
            "0000180f-0000-1000-8000-00805f9b34fb"
        )
        assert runtime.started[-1]["characteristic_uuid"] == (
            "00002a19-0000-1000-8000-00805f9b34fb"
        )
        assert runtime.stopped[-1]["service_uuid"] == (
            "0000180f-0000-1000-8000-00805f9b34fb"
        )
        assert runtime.stopped[-1]["characteristic_uuid"] == (
            "00002a19-0000-1000-8000-00805f9b34fb"
        )
        assert client._notify_callbacks == {}

    asyncio.run(run_test())


def test_aruba_bleak_client_stop_notify_clears_local_callback_when_runtime_lost_it(
    monkeypatch,
):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        async def async_stop_gatt_notify(self, **kwargs):
            return {
                "sent": False,
                "status": "not_registered",
                "status_string": "Aruba notification callback was not registered",
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )
        callback = lambda *_: None

        client._is_connected = True
        client._notify_callbacks[characteristic.uuid] = (
            characteristic.service_uuid,
            callback,
        )

        await client.stop_notify(characteristic)

        assert client._notify_callbacks == {}

    asyncio.run(run_test())


def test_aruba_bleak_client_start_notify_fails_if_disconnected_before_registration(
    monkeypatch,
):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.forgotten = []

        def is_device_active(self, source, address):
            return self.active

        async def async_start_gatt_notify(self, **kwargs):
            self.active = False
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        client._is_connected = True

        try:
            await client.start_notify(characteristic, lambda *_: None)
        except BleakError as err:
            assert "disconnected while enabling notifications" in str(err)
        else:
            raise AssertionError("start_notify should fail if Aruba disconnects first")

        assert client.is_connected is False
        assert client._notify_callbacks == {}
        assert len(runtime.forgotten) == 1
        assert runtime.forgotten[0]["ap_mac"] == "02:00:00:00:00:01"
        assert runtime.forgotten[0]["device_mac"] == "02:00:00:00:01:01"
        assert runtime.forgotten[0]["service_uuid"] == characteristic.service_uuid
        assert runtime.forgotten[0]["characteristic_uuid"] == characteristic.uuid

    asyncio.run(run_test())


def test_aruba_bleak_client_notify_does_not_swallow_callback_type_error(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.started = []

        async def async_start_gatt_notify(self, **kwargs):
            self.started.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        def callback(sender, value):
            raise TypeError("callback body failed")

        client._is_connected = True
        client.services = _FakeServiceCollection(characteristic)

        await client.start_notify(characteristic.uuid, callback)

        with pytest.raises(TypeError, match="callback body failed"):
            runtime.started[-1]["callback"](SimpleNamespace(value=b"\x02"))

    asyncio.run(run_test())


def test_aruba_bleak_client_accepts_ble_device_object(monkeypatch):
    _install_fake_bleak(monkeypatch)

    client_cls = create_aruba_bleak_client(object(), "02:00:00:00:00:01")
    client = client_cls(SimpleNamespace(address="02:00:00:00:01:01"))

    assert client.address == "02:00:00:00:01:01"
    assert client.name == "02:00:00:00:01:01"


def test_aruba_bleak_client_get_services_requires_connection(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    async def run_test():
        client_cls = create_aruba_bleak_client(object(), "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        try:
            await client.get_services()
        except BleakError as err:
            assert "not connected" in str(err)
        else:
            raise AssertionError("get_services should require a connected client")

        client._is_connected = True
        services = _FakeServiceCollection()
        client.services = services

        assert await client.get_services() is services

    asyncio.run(run_test())


def test_aruba_bleak_client_supports_bleak_retry_cache_methods(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    class Runtime:
        def __init__(self):
            self.cleared = []

        def clear_device_characteristics(self, source, address):
            self.cleared.append((source, address))
            return True

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        cached_services = build_service_collection([], advertisement_service_uuids={"fd3d"})

        client.set_cached_services(cached_services)
        assert client.services is cached_services
        assert client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None

        assert await client.clear_cache() is True
        assert client.services is not cached_services
        assert client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is None
        assert runtime.cleared == [("02:00:00:00:00:01", "02:00:00:00:01:01")]

        await client.set_connection_params(6, 12, 0, 400)

    asyncio.run(run_test())


def test_aruba_bleak_client_clear_cache_succeeds_if_runtime_clear_fails(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    class Runtime:
        def clear_device_characteristics(self, source, address):
            raise RuntimeError("runtime cache failed")

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        cached_services = build_service_collection([], advertisement_service_uuids={"fd3d"})

        client.set_cached_services(cached_services)
        assert client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None

        assert await client.clear_cache() is True
        assert client.services is not cached_services
        assert client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is None

    asyncio.run(run_test())


def test_aruba_bleak_client_mtu_uses_runtime_connection_update(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.mtu = None

        def mtu_for_device(self, source, address):
            assert source == "02:00:00:00:00:01"
            assert address == "02:00:00:00:01:01"
            return self.mtu

    runtime = Runtime()
    client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
    client = client_cls("02:00:00:00:01:01")

    assert client.mtu_size == 23

    runtime.mtu = 185
    assert client.mtu_size == 185


def test_aruba_bleak_client_notify_schedules_async_callback(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.started = []

        async def async_start_gatt_notify(self, **kwargs):
            self.started.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        values = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )

        async def callback(sender, value):
            await asyncio.sleep(0)
            values.append((sender, value))

        client._is_connected = True
        await client.start_notify(characteristic, callback)
        runtime.started[-1]["callback"](SimpleNamespace(value=b"\x64"))
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert values == [(characteristic, bytearray([100]))]

    asyncio.run(run_test())


def test_aruba_bleak_client_runtime_disconnect_supports_async_callback(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.listeners = []

        def is_device_active(self, source, address):
            return self.active

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append(listener)

            def unsubscribe():
                if listener in self.listeners:
                    self.listeners.remove(listener)

            return unsubscribe

        async def async_send_aruba_action(self, **kwargs):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

    async def run_test():
        disconnected = []
        runtime = Runtime()

        async def disconnected_callback(client):
            await asyncio.sleep(0)
            disconnected.append(client)

        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls(
            "02:00:00:00:01:01",
            disconnected_callback=disconnected_callback,
        )

        await client.connect()
        runtime.active = False
        runtime.listeners[0](object())
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert disconnected == [client]

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_callback_is_optional(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return False

    client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
    client = client_cls("02:00:00:00:01:01")
    client._is_connected = True
    del client._disconnected_callback

    assert client.is_connected is False


def test_aruba_bleak_client_disconnect_callback_supports_no_arg_wrapper(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return False

    called = []

    def disconnected_callback():
        called.append(True)

    client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
    client = client_cls(
        "02:00:00:00:01:01",
        disconnected_callback=disconnected_callback,
    )
    client._is_connected = True

    assert client.is_connected is False
    assert called == [True]


def test_aruba_bleak_client_set_disconnected_callback_replaces_callback(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return False

    initial = []
    replacement = []

    client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
    client = client_cls(
        "02:00:00:00:01:01",
        disconnected_callback=lambda closed_client: initial.append(closed_client),
    )
    client.set_disconnected_callback(lambda closed_client: replacement.append(closed_client))
    client._is_connected = True

    assert client.is_connected is False
    assert initial == []
    assert replacement == [client]


def test_aruba_bleak_client_set_disconnected_callback_accepts_none(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return False

    called = []
    client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
    client = client_cls(
        "02:00:00:00:01:01",
        disconnected_callback=lambda closed_client: called.append(closed_client),
    )
    client.set_disconnected_callback(None)
    client._is_connected = True

    assert client.is_connected is False
    assert called == []


def test_aruba_bleak_client_disconnect_callback_does_not_swallow_type_error(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return False

    def disconnected_callback(client):
        raise TypeError("disconnect callback body failed")

    client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
    client = client_cls(
        "02:00:00:00:01:01",
        disconnected_callback=disconnected_callback,
    )
    client._is_connected = True

    with pytest.raises(TypeError, match="disconnect callback body failed"):
        client.is_connected


def test_aruba_bleak_client_reports_disconnected_after_aruba_status(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True

        def is_device_active(self, source, address):
            return self.active

    runtime = Runtime()
    client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
    client = client_cls("02:00:00:00:01:01")

    client._is_connected = True
    assert client.is_connected is True

    runtime.active = False
    assert client.is_connected is False


def test_aruba_bleak_client_clears_stale_notify_before_gatt_after_status(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = False
            self.forgotten = []
            self.reads = []

        def is_device_active(self, source, address):
            return self.active

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

        async def async_gatt_read(self, **kwargs):
            self.reads.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
                "characteristic": {
                    "value": "64",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic = SimpleNamespace(
            service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
            uuid="00002a19-0000-1000-8000-00805f9b34fb",
        )
        callback = lambda *_: None

        client._is_connected = True
        client._notify_callbacks[characteristic.uuid] = (
            characteristic.service_uuid,
            callback,
        )

        try:
            await client.read_gatt_char(characteristic)
        except BleakError as err:
            assert "not connected" in str(err)
        else:
            raise AssertionError("read_gatt_char should fail after Aruba disconnect status")

        assert client._is_connected is False
        assert client._notify_callbacks == {}
        assert runtime.reads == []
        assert runtime.forgotten == [
            {
                "ap_mac": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": "0000180f-0000-1000-8000-00805f9b34fb",
                "characteristic_uuid": "00002a19-0000-1000-8000-00805f9b34fb",
                "callback": callback,
            }
        ]

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_is_noop_after_status_disconnect(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = False
            self.actions = []
            self.forgotten = []

        def is_device_active(self, source, address):
            return self.active

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

        async def async_send_aruba_action(self, **kwargs):
            self.actions.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic_uuid = "00002a19-0000-1000-8000-00805f9b34fb"
        service_uuid = "0000180f-0000-1000-8000-00805f9b34fb"

        client._is_connected = True
        client._notify_callbacks[characteristic_uuid] = (service_uuid, lambda *_: None)

        await client.disconnect()

        assert client._is_connected is False
        assert client._notify_callbacks == {}
        assert runtime.actions == []
        assert len(runtime.forgotten) == 1

    asyncio.run(run_test())


def test_aruba_bleak_client_runtime_disconnect_listener_fires_callback(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.listeners = []
            self.forgotten = []

        def is_device_active(self, source, address):
            return self.active

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append((source, device_mac, listener))

            def unsubscribe():
                if (source, device_mac, listener) in self.listeners:
                    self.listeners.remove((source, device_mac, listener))

            return unsubscribe

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

        async def async_send_aruba_action(self, **kwargs):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

    async def run_test():
        disconnected = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls(
            "02:00:00:00:01:01",
            disconnected_callback=lambda closed_client: disconnected.append(closed_client),
        )
        characteristic_uuid = "00002a19-0000-1000-8000-00805f9b34fb"
        service_uuid = "0000180f-0000-1000-8000-00805f9b34fb"

        assert await client.connect() is True
        client._notify_callbacks[characteristic_uuid] = (service_uuid, lambda *_: None)
        assert client.is_connected is True
        assert len(runtime.listeners) == 1

        runtime.active = False
        runtime.listeners[0][2](object())

        assert client.is_connected is False
        assert client._notify_callbacks == {}
        assert disconnected == [client]
        assert runtime.listeners == []
        assert len(runtime.forgotten) == 1

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_returns_true_when_already_disconnected(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []

        async def async_send_aruba_action(self, **kwargs):
            self.actions.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        assert await client.disconnect() is True
        assert runtime.actions == []

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_cleans_stale_notifications(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []
            self.forgotten = []

        async def async_send_aruba_action(self, **kwargs):
            self.actions.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic_uuid = "00002a19-0000-1000-8000-00805f9b34fb"
        service_uuid = "0000180f-0000-1000-8000-00805f9b34fb"
        callback = lambda *_: None
        client._is_connected = False
        client._notify_callbacks[characteristic_uuid] = (service_uuid, callback)

        assert await client.disconnect() is True

        assert runtime.actions == []
        assert client._notify_callbacks == {}
        assert runtime.forgotten == [
            {
                "ap_mac": "02:00:00:00:00:01",
                "device_mac": "02:00:00:00:01:01",
                "service_uuid": service_uuid,
                "characteristic_uuid": characteristic_uuid,
                "callback": callback,
            }
        ]

    asyncio.run(run_test())


def test_aruba_bleak_client_disconnect_clears_notify_callbacks_if_runtime_forget_fails(
    monkeypatch,
):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        async def async_send_aruba_action(self, **kwargs):
            raise AssertionError("disconnect action should not be sent")

        def forget_gatt_notify_callback(self, **kwargs):
            raise RuntimeError("forget failed")

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        characteristic_uuid = "00002a19-0000-1000-8000-00805f9b34fb"
        service_uuid = "0000180f-0000-1000-8000-00805f9b34fb"
        callback = lambda *_: None
        client._is_connected = False
        client._notify_callbacks[characteristic_uuid] = (service_uuid, callback)

        assert await client.disconnect() is True
        assert client._notify_callbacks == {}

    asyncio.run(run_test())


def test_aruba_bleak_client_connect_returns_true_when_already_connected(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []
            self.discoveries = 0

        def is_device_active(self, source, address):
            return True

        async def async_send_aruba_action(self, **kwargs):
            self.actions.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            self.discoveries += 1
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")
        client._is_connected = True

        assert await client.connect() is True
        assert client.is_connected is True
        assert runtime.actions == []
        assert runtime.discoveries == 0

    asyncio.run(run_test())


def test_aruba_bleak_client_accepts_idempotent_action_results(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.connected = False
            self.actions = []

        def is_device_active(self, source, address):
            return self.connected

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append(request.action_type)
            if request.action_type == "bleConnect":
                self.connected = True
                return {
                    "sent": True,
                    "result": {
                        "received": True,
                        "status": "alreadyConnected",
                    },
                }
            self.connected = False
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "deviceDisconnected",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        assert await client.connect() is True
        assert client.is_connected is True
        assert await client.disconnect() is True
        assert client.is_connected is False
        assert runtime.actions == ["bleConnect", ACTION_BLE_DISCONNECT]

    asyncio.run(run_test())


def test_aruba_bleak_client_accepts_local_already_connected_response(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.connected = False
            self.discoveries = 0

        def is_device_active(self, source, address):
            return self.connected

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.connected = True
            return {
                "sent": False,
                "status": "alreadyConnected",
                "status_string": "Device is already connected through this Aruba AP",
            }

        async def async_wait_for_device_characteristics(self, address, *, source=None):
            self.discoveries += 1
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        assert await client.connect() is True
        assert client.is_connected is True
        assert runtime.discoveries == 1

    asyncio.run(run_test())


def test_aruba_bleak_client_rejects_local_no_connection_slots_response(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.discoveries = 0

        def is_device_active(self, source, address):
            return False

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            return {
                "sent": False,
                "status": "noMoreConnectionSlots",
                "status_string": "Another BLE device is already connected through this Aruba AP",
            }

        async def async_wait_for_device_characteristics(self, address, *, source=None):
            self.discoveries += 1
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:02")

        try:
            await client.connect()
        except BleakError as err:
            assert "noMoreConnectionSlots" in str(err)
            assert "Another BLE device is already connected" in str(err)
        else:
            raise AssertionError("connect should fail when the Aruba AP slot is full")

        assert client.is_connected is False
        assert runtime.discoveries == 0

    asyncio.run(run_test())


def test_aruba_bleak_client_connect_rejects_pairing_request(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []

        async def async_send_aruba_action(self, **kwargs):
            self.actions.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        try:
            await client.connect(pair=True)
        except BleakError as err:
            assert "pairing is not implemented" in str(err)
        else:
            raise AssertionError("connect(pair=True) should fail explicitly")

        assert runtime.actions == []
        assert client.is_connected is False

    asyncio.run(run_test())


def test_aruba_bleak_client_connect_fails_if_disconnected_during_discovery(monkeypatch):
    BleakError = _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.listeners = []

        def is_device_active(self, source, address):
            return self.active

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append(listener)

            def unsubscribe():
                if listener in self.listeners:
                    self.listeners.remove(listener)

            return unsubscribe

        async def async_send_aruba_action(self, **kwargs):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            self.active = False
            self.listeners[0](object())
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        try:
            await client.connect()
        except BleakError as err:
            assert "disconnected during service discovery" in str(err)
        else:
            raise AssertionError("connect should fail if Aruba disconnects during discovery")

        assert client.is_connected is False
        assert runtime.listeners == []

    asyncio.run(run_test())


def test_aruba_bleak_client_connect_failure_sends_best_effort_disconnect(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.actions = []
            self.listeners = []

        def is_device_active(self, source, address):
            return self.active

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append(listener)

            def unsubscribe():
                if listener in self.listeners:
                    self.listeners.remove(listener)

            return unsubscribe

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append((ap_mac, request, wait_result))
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            raise RuntimeError("discovery crashed")

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        try:
            await client.connect()
        except RuntimeError as err:
            assert "discovery crashed" in str(err)
        else:
            raise AssertionError("connect should propagate discovery failure")

        assert client.is_connected is False
        assert runtime.listeners == []
        assert len(runtime.actions) == 2
        assert runtime.actions[0][1].action_type == "bleConnect"
        assert runtime.actions[0][2] is True
        assert runtime.actions[1][1].action_type == ACTION_BLE_DISCONNECT
        assert runtime.actions[1][2] is False

    asyncio.run(run_test())


def test_aruba_bleak_client_connect_cancellation_cleans_up(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.actions = []
            self.listeners = []

        def is_device_active(self, source, address):
            return self.active

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append(listener)

            def unsubscribe():
                if listener in self.listeners:
                    self.listeners.remove(listener)

            return unsubscribe

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append((ap_mac, request, wait_result))
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            raise asyncio.CancelledError

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        try:
            await client.connect()
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("connect should propagate cancellation")

        assert client.is_connected is False
        assert runtime.listeners == []
        assert len(runtime.actions) == 2
        assert runtime.actions[1][1].action_type == ACTION_BLE_DISCONNECT
        assert runtime.actions[1][2] is False

    asyncio.run(run_test())


def test_aruba_bleak_client_normalizes_ble_device_address(monkeypatch):
    _install_fake_bleak(monkeypatch)

    class Runtime:
        def __init__(self):
            self.actions = []
            self.waited = []
            self.listeners = []

        def is_device_active(self, source, address):
            return True

        def add_device_disconnect_listener(self, source, device_mac, listener):
            self.listeners.append((source, device_mac, listener))
            return lambda: None

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            self.actions.append((ap_mac, request))
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            self.waited.append(address)
            return []

    async def run_test():
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "020000000001")
        client = client_cls(SimpleNamespace(address="020000000101"))

        await client.connect()

        assert client.address == "02:00:00:00:01:01"
        assert runtime.actions[0][0] == "020000000001"
        assert runtime.actions[0][1].device_mac == "02:00:00:00:01:01"
        assert runtime.waited == ["02:00:00:00:01:01"]
        assert runtime.listeners[0][1] == "02:00:00:00:01:01"

    asyncio.run(run_test())


def test_aruba_bleak_client_uses_runtime_advertised_services_for_switchbot_fallback(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    class Runtime:
        def is_device_active(self, source, address):
            return True

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

        def service_uuids_for_device(self, address):
            return {"0000fd3d-0000-1000-8000-00805f9b34fb"}

    async def run_test():
        client_cls = create_aruba_bleak_client(Runtime(), "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        await client.connect()

        assert client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None
        assert client.services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID) is not None

    asyncio.run(run_test())


def test_aruba_bleak_client_supports_switchbot_command_flow(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    class Runtime:
        def __init__(self):
            self.active = True
            self.starts = []
            self.writes = []
            self.registered = []
            self.forgotten = []

        def is_device_active(self, source, address):
            return self.active

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

        def service_uuids_for_device(self, address):
            return {"fd3d"}

        async def async_start_gatt_notify(self, **kwargs):
            self.starts.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        def register_gatt_notify_callback(self, **kwargs):
            self.registered.append(kwargs)
            return True

        def forget_gatt_notify_callback(self, **kwargs):
            self.forgotten.append(kwargs)
            return True

        async def async_gatt_write(self, **kwargs):
            self.writes.append(kwargs)
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

    async def run_test():
        values = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        await client.connect()
        read_char = client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID)
        write_char = client.services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID)

        await client.start_notify(
            read_char,
            lambda sender, value: values.append((sender.uuid, bytes(value))),
        )
        await client.write_gatt_char(write_char, bytes.fromhex("570f4e0101000000"))
        runtime.registered[-1]["callback"](SimpleNamespace(value=b"\x01"))

        assert runtime.starts == []
        assert runtime.registered[-1]["service_uuid"] == read_char.service_uuid
        assert runtime.registered[-1]["characteristic_uuid"] == SWITCHBOT_READ_CHAR_UUID
        assert runtime.writes[-1]["service_uuid"] == write_char.service_uuid
        assert runtime.writes[-1]["characteristic_uuid"] == SWITCHBOT_WRITE_CHAR_UUID
        assert runtime.writes[-1]["with_response"] is False
        assert runtime.writes[-1]["wait_result"] is False
        assert values == [(SWITCHBOT_READ_CHAR_UUID, b"\x01")]

        await client.stop_notify(read_char)
        assert runtime.forgotten[-1]["characteristic_uuid"] == SWITCHBOT_READ_CHAR_UUID

    asyncio.run(run_test())


def test_aruba_bleak_client_ignores_empty_notification_values(monkeypatch):
    _install_fake_bleak_services(monkeypatch)

    class Runtime:
        def __init__(self):
            self.registered = []

        def is_device_active(self, source, address):
            return True

        async def async_send_aruba_action(self, *, ap_mac, request, wait_result=True):
            return {
                "sent": True,
                "result": {
                    "received": True,
                    "status": "success",
                },
            }

        async def async_wait_for_device_characteristics(self, address):
            return []

        def service_uuids_for_device(self, address):
            return {"fd3d"}

        def register_gatt_notify_callback(self, **kwargs):
            self.registered.append(kwargs)
            return True

    async def run_test():
        values = []
        runtime = Runtime()
        client_cls = create_aruba_bleak_client(runtime, "02:00:00:00:00:01")
        client = client_cls("02:00:00:00:01:01")

        await client.connect()
        read_char = client.services.get_characteristic(SWITCHBOT_READ_CHAR_UUID)
        await client.start_notify(
            read_char,
            lambda sender, value: values.append(bytes(value)),
        )

        runtime.registered[-1]["callback"](SimpleNamespace(value=b""))
        runtime.registered[-1]["callback"](SimpleNamespace(value=b"\x0f"))

        assert values == [b"\x0f"]

    asyncio.run(run_test())


def test_aruba_bleak_client_instantiates_with_real_bleak_when_available():
    pytest.importorskip("bleak")

    client_cls = create_aruba_bleak_client(object(), "02:00:00:00:00:01")
    client = client_cls("020000000101")

    assert client.address == "02:00:00:00:01:01"
    assert client.mtu_size == 23


def test_build_service_collection_uses_real_bleak_when_available():
    pytest.importorskip("bleak")

    reporter = Reporter(
        name=None,
        mac="02:00:00:00:00:01",
        ipv4=None,
        ipv6=None,
        hardware_type=None,
        software_version=None,
        software_build=None,
        timestamp=None,
    )

    services = build_service_collection(
        [
            ArubaCharacteristic(
                reporter=reporter,
                device_mac="02:00:00:00:01:01",
                service_uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
                value=b"\x64",
                description="Battery Level",
                properties=("read", "notify"),
            )
        ]
    )

    assert services.get_service("0000180f-0000-1000-8000-00805f9b34fb") is not None
    assert (
        services.get_characteristic("00002a19-0000-1000-8000-00805f9b34fb")
        is not None
    )


def test_switchbot_fallback_service_collection_uses_real_bleak_when_available():
    pytest.importorskip("bleak")

    services = build_service_collection([], advertisement_service_uuids={"fd3d"})

    assert services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None
    assert services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID) is not None
