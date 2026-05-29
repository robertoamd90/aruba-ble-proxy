from custom_components.aruba_ble_proxy.ble_parser import parse_advertisement_data


def test_parse_local_name_and_uuid16():
    payload = bytes.fromhex("0201060303d2fc08094154435f313233")

    advertisement = parse_advertisement_data(payload)

    assert advertisement.local_name == "ATC_123"
    assert advertisement.service_uuids == ("0000fcd2-0000-1000-8000-00805f9b34fb",)


def test_parse_manufacturer_data():
    payload = bytes.fromhex("02010608ff4c000215010203")

    advertisement = parse_advertisement_data(payload)

    assert advertisement.manufacturer_data == {0x004C: bytes.fromhex("0215010203")}


def test_parse_service_data_16():
    payload = bytes.fromhex("0201060716d2fc40010203")

    advertisement = parse_advertisement_data(payload)

    assert advertisement.service_data == {
        "0000fcd2-0000-1000-8000-00805f9b34fb": bytes.fromhex("40010203")
    }


def test_malformed_ad_structure_stops_without_error():
    payload = bytes.fromhex("02010609ff4c00")

    advertisement = parse_advertisement_data(payload)

    assert advertisement.raw_ad_structures == ((0x01, bytes.fromhex("06")),)
