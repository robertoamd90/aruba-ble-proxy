from custom_components.aruba_ble_proxy.ha_payload import event_to_bluetooth_payload
from custom_components.aruba_ble_proxy.models import (
    ArubaBleEvent,
    BleAdvertisement,
    BleFrameType,
    MacAddrType,
    Reporter,
)


def test_event_to_bluetooth_payload():
    event = ArubaBleEvent(
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
            service_uuids=("0000fcd2-0000-1000-8000-00805f9b34fb",),
            manufacturer_data={2409: b"\x01\x02"},
            service_data={"0000fcd2-0000-1000-8000-00805f9b34fb": b"\x03\x04"},
        ),
    )

    payload = event_to_bluetooth_payload(event)

    assert payload.name == "LYWSD03MMC"
    assert payload.address == "02:00:00:00:01:03"
    assert payload.rssi == -61
    assert payload.source == "02:00:00:00:00:01"
    assert payload.connectable is True
    assert payload.raw == b"\x02\x01\x06"


def test_event_to_bluetooth_payload_marks_non_connectable_frames():
    event = ArubaBleEvent(
        reporter=Reporter(
            name="ap-1",
            mac="02:00:00:00:00:01",
            ipv4=None,
            ipv6=None,
            hardware_type=None,
            software_version=None,
            software_build=None,
            timestamp=None,
        ),
        address="02:00:00:00:01:03",
        frame_type=BleFrameType.ADV_NONCONN_IND,
        rssi=-61,
        address_type=MacAddrType.PUBLIC,
        apb_mac=None,
        payload=b"\x02\x01\x06",
        advertisement=BleAdvertisement(),
    )

    payload = event_to_bluetooth_payload(event)

    assert payload.connectable is False
