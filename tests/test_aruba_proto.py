import pytest

import custom_components.aruba_ble_proxy.aruba_proto as aruba_proto
from custom_components.aruba_ble_proxy.aruba_proto import ArubaTelemetryDecoder, _ArubaPb2
from custom_components.aruba_ble_proxy.models import BleFrameType, MacAddrType


class FakeMeta:
    access_token = "secret"


class FakeReporter:
    name = "ap-01"
    mac = bytes.fromhex("aabbccddeeff")
    ipv4 = "192.0.2.10"
    ipv6 = ""
    hwType = "AP-TEST"
    swVersion = "test-version"
    swBuild = ""
    time = 123


class FakeBleData:
    mac = bytes.fromhex("112233445566")
    frameType = 0
    data = bytes.fromhex("0201060303d2fc08094154435f313233")
    rssi = -61
    addrType = 0
    apbMac = b""


class FakeTelemetry:
    meta = FakeMeta()
    reporter = FakeReporter()
    bleData = [FakeBleData()]

    def ParseFromString(self, message):
        return None


def test_decoder_emits_normalized_ble_event(monkeypatch):
    monkeypatch.setattr(
        aruba_proto,
        "_load_aruba_pb2",
        lambda: _ArubaPb2(telemetry_cls=FakeTelemetry),
    )

    events = ArubaTelemetryDecoder(access_token="secret").decode(b"fake")

    assert len(events) == 1
    event = events[0]
    assert event.source == "aa:bb:cc:dd:ee:ff"
    assert event.address == "11:22:33:44:55:66"
    assert event.frame_type is BleFrameType.ADV_IND
    assert event.address_type is MacAddrType.PUBLIC
    assert event.rssi == -61
    assert event.advertisement.local_name == "ATC_123"
    assert event.advertisement.service_uuids == (
        "0000fcd2-0000-1000-8000-00805f9b34fb",
    )


def test_decoder_rejects_invalid_access_token(monkeypatch):
    monkeypatch.setattr(
        aruba_proto,
        "_load_aruba_pb2",
        lambda: _ArubaPb2(telemetry_cls=FakeTelemetry),
    )

    decoder = ArubaTelemetryDecoder(access_token="other-secret")

    with pytest.raises(PermissionError):
        decoder.decode(b"fake")
