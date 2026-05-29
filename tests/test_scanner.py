import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace

from custom_components.aruba_ble_proxy.ha_payload import BluetoothPayload
from custom_components.aruba_ble_proxy.scanner import ArubaBleRemoteScanner


@dataclass(frozen=True)
class _Details:
    name: str = "before"


def _payload() -> BluetoothPayload:
    return BluetoothPayload(
        name="Meter",
        address="02:00:00:00:01:01",
        rssi=-70,
        manufacturer_data={2409: b"\x01"},
        service_data={"0000180f-0000-1000-8000-00805f9b34fb": b"\x64"},
        service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"],
        source="02:00:00:00:00:01",
        connectable=True,
        time=123.4,
        tx_power=None,
        raw=b"\x02\x01\x06",
    )


def _install_fake_bluetooth(monkeypatch, scanner_base):
    @dataclass(frozen=True)
    class HaBluetoothConnector:
        client: type
        source: str
        can_connect: object

    bluetooth = types.ModuleType("homeassistant.components.bluetooth")
    bluetooth.BaseHaRemoteScanner = scanner_base
    bluetooth.BluetoothScanningMode = SimpleNamespace(PASSIVE="passive")
    bluetooth.HaBluetoothConnector = HaBluetoothConnector

    components = types.ModuleType("homeassistant.components")
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.components = components
    components.bluetooth = bluetooth

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.bluetooth", bluetooth)


def test_remote_scanner_forwards_payload_to_legacy_internal_method(monkeypatch):
    class LegacyScanner:
        calls = []

        def __init__(self, **kwargs):
            self.connectable = kwargs["connectable"]
            self.details = _Details()

        def async_setup(self):
            return lambda: None

        def _async_on_advertisement_internal(self, *args):
            self.calls.append(args)

    _install_fake_bluetooth(monkeypatch, LegacyScanner)

    scanner = ArubaBleRemoteScanner("02:00:00:00:00:01")
    scanner.async_on_payload(_payload())

    assert LegacyScanner.calls == [
        (
            "02:00:00:00:01:01",
            -70,
            "Meter",
            ["0000180f-0000-1000-8000-00805f9b34fb"],
            {"0000180f-0000-1000-8000-00805f9b34fb": b"\x64"},
            {2409: b"\x01"},
            None,
            {},
            123.4,
            b"\x02\x01\x06",
        )
    ]


def test_remote_scanner_supports_internal_method_without_raw_payload(monkeypatch):
    class InternalScanner:
        calls = []

        def __init__(self, **kwargs):
            self.connectable = kwargs["connectable"]
            self.details = _Details()

        def async_setup(self):
            return lambda: None

        def _async_on_advertisement_internal(
            self,
            address,
            rssi,
            local_name,
            service_uuids,
            service_data,
            manufacturer_data,
            tx_power,
            details,
            advertisement_monotonic_time,
        ):
            self.calls.append(
                (
                    address,
                    rssi,
                    local_name,
                    service_uuids,
                    service_data,
                    manufacturer_data,
                    tx_power,
                    details,
                    advertisement_monotonic_time,
                )
            )

    _install_fake_bluetooth(monkeypatch, InternalScanner)

    scanner = ArubaBleRemoteScanner("02:00:00:00:00:01")
    scanner.async_on_payload(_payload())

    assert InternalScanner.calls == [
        (
            "02:00:00:00:01:01",
            -70,
            "Meter",
            ["0000180f-0000-1000-8000-00805f9b34fb"],
            {"0000180f-0000-1000-8000-00805f9b34fb": b"\x64"},
            {2409: b"\x01"},
            None,
            {},
            123.4,
        )
    ]


def test_remote_scanner_forwards_payload_to_current_habluetooth_method(monkeypatch):
    class CurrentScanner:
        calls = []

        def __init__(self, **kwargs):
            self.connectable = kwargs["connectable"]
            self.details = _Details()

        def async_setup(self):
            return lambda: None

        def _async_on_advertisement(self, *args):
            self.calls.append(args)

    _install_fake_bluetooth(monkeypatch, CurrentScanner)

    scanner = ArubaBleRemoteScanner("02:00:00:00:00:01")
    scanner.async_on_payload(_payload())

    assert CurrentScanner.calls == [
        (
            "02:00:00:00:01:01",
            -70,
            "Meter",
            ["0000180f-0000-1000-8000-00805f9b34fb"],
            {"0000180f-0000-1000-8000-00805f9b34fb": b"\x64"},
            {2409: b"\x01"},
            None,
            {},
            123.4,
        )
    ]


def test_remote_scanner_connectable_connector_tracks_one_active_slot(monkeypatch):
    class CurrentScanner:
        def __init__(self, **kwargs):
            self.adapter = kwargs["adapter"]
            self.connector = kwargs["connector"]
            self.connectable = kwargs["connectable"]
            self.details = _Details()
            self._connect_in_progress = {}

        def async_setup(self):
            return lambda: None

        def _async_on_advertisement(self, *args):
            pass

    class Runtime:
        def __init__(self):
            self.connected = True
            self.active_devices = []

        def can_connect_source(self, source):
            return self.connected

        def active_devices_for_source(self, source):
            return list(self.active_devices)

    _install_fake_bluetooth(monkeypatch, CurrentScanner)
    runtime = Runtime()

    scanner = ArubaBleRemoteScanner(
        "02:00:00:00:00:01",
        runtime=runtime,
        connectable=True,
    )

    assert scanner.connectable is True
    assert scanner.scanner.connector.can_connect() is True
    allocations = scanner.scanner.get_allocations()
    assert allocations.slots == 1
    assert allocations.free == 1
    assert allocations.allocated == []

    scanner.scanner._connect_in_progress["02:00:00:00:01:01"] = 1
    assert scanner.scanner.connector.can_connect() is False
    allocations = scanner.scanner.get_allocations()
    assert allocations.free == 0
    assert allocations.allocated == ["02:00:00:00:01:01"]

    scanner.scanner._connect_in_progress.clear()
    runtime.active_devices = ["02:00:00:00:01:02"]
    allocations = scanner.scanner.get_allocations()
    assert allocations.free == 0
    assert allocations.allocated == ["02:00:00:00:01:02"]
