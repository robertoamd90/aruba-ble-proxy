"""Optional integration tests with the HA 2026.11 Bluetooth dependencies.

These exercise the real compiled parser and scanner without a radio or HA Core.
Install in a test environment with:
    pip install -e '.[dev]' habluetooth==7.1.2 bluetooth-data-tools==1.29.24 bleak==3.0.2
"""
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

import pytest

habluetooth = pytest.importorskip("habluetooth")
from habluetooth.central_manager import CentralBluetoothManager

from custom_components.aruba_ble_proxy.ble_parser import parse_advertisement_data
from custom_components.aruba_ble_proxy.aruba_proto import ArubaTelemetryDecoder
from custom_components.aruba_ble_proxy.ha_payload import BluetoothPayload, event_to_bluetooth_payload
from custom_components.aruba_ble_proxy.scanner import ArubaBleRemoteScanner

ADDRESS = "02:00:00:00:01:01"
SOURCE = "02:00:00:00:00:01"
UUID16 = "0000180f-0000-1000-8000-00805f9b34fb"
UUID32 = "12345678-0000-1000-8000-00805f9b34fb"
UUID128 = "00112233-4455-6677-8899-aabbccddeeff"


def ad(kind, value):
    return bytes((len(value) + 1, kind)) + value


def payload(raw):
    parsed = parse_advertisement_data(raw)
    return BluetoothPayload(
        name=parsed.local_name, address=ADDRESS, rssi=-60,
        manufacturer_data=dict(parsed.manufacturer_data),
        service_data=dict(parsed.service_data), service_uuids=list(parsed.service_uuids),
        source=SOURCE, connectable=True, time=100., tx_power=parsed.tx_power,
        raw=raw,
    )


@pytest.fixture
def manager(monkeypatch):
    manager = habluetooth.BluetoothManager()
    monkeypatch.setattr(CentralBluetoothManager, "manager", manager)
    return manager


@pytest.mark.parametrize("path", ["raw", "legacy"])
@pytest.mark.parametrize("reverse", [False, True])
def test_real_scanner_merges_named_advertisement_and_nameless_response(manager, path, reverse):
    wrapper = ArubaBleRemoteScanner(SOURCE)
    scanner = wrapper.scanner
    if path != "raw":
        method = "_async_on_advertisement"
        wrapper._scanner = SimpleNamespace(**{method: getattr(scanner, method)})
    named = payload(ad(9, b"GVH5075_1234") + ad(255, b"\x01\x00\x10\x20"))
    nameless = payload(ad(255, b"\x4c\x00\x02\x15"))
    frames = [named, nameless] if not reverse else [nameless, named]
    for index, frame in enumerate(frames):
        wrapper.async_on_payload(replace(frame, time=100. + index))
    # A later nameless frame must retain the name in both orders.
    wrapper.async_on_payload(replace(nameless, time=103.))
    device, adv = scanner.discovered_devices_and_advertisement_data[ADDRESS]
    assert device.name == adv.local_name == "GVH5075_1234"
    assert adv.manufacturer_data == {1: b"\x10\x20", 76: b"\x02\x15"}
    assert device.details["source"] == SOURCE


def test_real_raw_parser_all_data_types_and_name_precedence(manager):
    raw = b"".join([
        ad(9, b"Complete name"), ad(8, b"Short"),
        ad(3, b"\x0f\x18"), ad(5, bytes.fromhex("78563412")),
        ad(7, UUID(UUID128).bytes[::-1]),
        ad(22, b"\x0f\x18\x64"), ad(32, bytes.fromhex("78563412") + b"\x42"),
        ad(33, UUID(UUID128).bytes[::-1] + b"\x99"),
        ad(255, b"\x4c\x00\x02\x15"), ad(10, b"\xf4"), b"\x00\x00",
    ])
    wrapper = ArubaBleRemoteScanner(SOURCE)
    decoder = ArubaTelemetryDecoder(access_token="test")
    telemetry = decoder._pb.telemetry_cls()
    telemetry.meta.access_token = "test"
    telemetry.meta.version = 1
    telemetry.reporter.mac = bytes.fromhex(SOURCE.replace(":", ""))
    telemetry.bleData.add(mac=bytes.fromhex(ADDRESS.replace(":", "")), data=raw, rssi=-60)
    event, = decoder.decode(telemetry.SerializeToString())
    forwarded = event_to_bluetooth_payload(event)
    assert forwarded.raw == raw
    wrapper.async_on_payload(forwarded)
    device, adv = wrapper.scanner.discovered_devices_and_advertisement_data[ADDRESS]
    assert device.name == "Complete name"
    assert set(adv.service_uuids) == {UUID16, UUID32, UUID128}
    assert adv.service_data == {UUID16: b"\x64", UUID32: b"\x42", UUID128: b"\x99"}
    assert adv.manufacturer_data == {76: b"\x02\x15"}
    assert adv.tx_power == -12
    assert wrapper.scanner.serialize_discovered_devices().discovered_device_raw[ADDRESS] == raw


@pytest.mark.parametrize("raw", [b"", b"\x00", b"\xff", b"\x09\xff\x4c\x00", b"\x01\xff", b"\x02\x01\x06\x09\xff\x4c\x00"])
def test_real_parser_empty_malformed_and_truncated_packets(manager, raw):
    wrapper = ArubaBleRemoteScanner(SOURCE)
    wrapper.async_on_payload(payload(raw))
    device, adv = wrapper.scanner.discovered_devices_and_advertisement_data[ADDRESS]
    assert device.name is None
    assert adv.manufacturer_data == {}
    # A damaged packet must not poison processing of the next valid one.
    wrapper.async_on_payload(payload(ad(9, b"Recovered")))
    assert device.name == "Recovered"


@pytest.mark.parametrize("connectable", [False, True])
def test_real_scanners_keep_sources_separate_during_repeated_packets(manager, connectable):
    runtime = SimpleNamespace(
        can_connect_source=lambda source: True,
        active_devices_for_source=lambda source: [ADDRESS],
        connection_slots_for_source=lambda source: 2,
    )
    first = ArubaBleRemoteScanner(SOURCE, runtime=runtime, connectable=connectable)
    second_source = "02:00:00:00:00:02"
    second = ArubaBleRemoteScanner(second_source, runtime=runtime, connectable=connectable)
    raw = ad(9, b"Meter") + ad(255, b"\x01\x00\x42")
    frame = payload(raw)
    first.async_on_payload(frame)
    device, initial = first.scanner.discovered_devices_and_advertisement_data[ADDRESS]
    for index in range(1000):
        first.async_on_payload(replace(frame, rssi=-70, time=101. + index))
    second.async_on_payload(replace(frame, source=second_source))
    repeated_device, repeated = first.scanner.discovered_devices_and_advertisement_data[ADDRESS]
    other_device, _ = second.scanner.discovered_devices_and_advertisement_data[ADDRESS]
    assert repeated_device is device
    assert repeated.manufacturer_data is initial.manufacturer_data
    assert repeated.rssi == -70
    assert first.scanner.discovered_device_timestamps[ADDRESS] == 1100.
    assert len(first.scanner.discovered_devices) == len(second.scanner.discovered_devices) == 1
    assert device is not other_device
    assert device.details["source"] == SOURCE
    assert other_device.details["source"] == second_source
    assert first.connectable is connectable
    if connectable:
        assert first.scanner.connector.can_connect()
        assert first.scanner.get_allocations().allocated == [ADDRESS]
        assert first.scanner.get_allocations().free == 1
