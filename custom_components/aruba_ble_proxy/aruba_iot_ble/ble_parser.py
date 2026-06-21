from __future__ import annotations

from uuid import UUID

from .models import BleAdvertisement


UUID16_AD_TYPES = {0x02, 0x03}
UUID32_AD_TYPES = {0x04, 0x05}
UUID128_AD_TYPES = {0x06, 0x07}
LOCAL_NAME_AD_TYPES = {0x08, 0x09}
SERVICE_DATA_16_AD_TYPE = 0x16
SERVICE_DATA_32_AD_TYPE = 0x20
SERVICE_DATA_128_AD_TYPE = 0x21
TX_POWER_AD_TYPE = 0x0A
MANUFACTURER_DATA_AD_TYPE = 0xFF


def parse_advertisement_data(payload: bytes) -> BleAdvertisement:
    """Parse BLE advertising data into generic AD structures.

    The parser intentionally does not interpret device semantics. It only
    extracts standard BLE AD fields so Home Assistant can decide what to do.
    """
    local_name: str | None = None
    tx_power: int | None = None
    service_uuids: list[str] = []
    manufacturer_data: dict[int, bytes] = {}
    service_data: dict[str, bytes] = {}
    raw_ad_structures: list[tuple[int, bytes]] = []

    for ad_type, data in iter_ad_structures(payload):
        raw_ad_structures.append((ad_type, data))

        if ad_type in LOCAL_NAME_AD_TYPES:
            local_name = data.decode("utf-8", "replace")
        elif ad_type == TX_POWER_AD_TYPE and len(data) >= 1:
            tx_power = int.from_bytes(data[0:1], "little", signed=True)
        elif ad_type in UUID16_AD_TYPES:
            service_uuids.extend(_parse_uuid16_list(data))
        elif ad_type in UUID32_AD_TYPES:
            service_uuids.extend(_parse_uuid32_list(data))
        elif ad_type in UUID128_AD_TYPES:
            service_uuids.extend(_parse_uuid128_list(data))
        elif ad_type == MANUFACTURER_DATA_AD_TYPE and len(data) >= 2:
            company_id = int.from_bytes(data[0:2], "little")
            manufacturer_data[company_id] = data[2:]
        elif ad_type == SERVICE_DATA_16_AD_TYPE and len(data) >= 2:
            service_data[_uuid16_to_str(data[0:2])] = data[2:]
        elif ad_type == SERVICE_DATA_32_AD_TYPE and len(data) >= 4:
            service_data[_uuid32_to_str(data[0:4])] = data[4:]
        elif ad_type == SERVICE_DATA_128_AD_TYPE and len(data) >= 16:
            service_data[_uuid128_to_str(data[0:16])] = data[16:]

    return BleAdvertisement(
        local_name=local_name,
        tx_power=tx_power,
        service_uuids=tuple(dict.fromkeys(service_uuids)),
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        raw_ad_structures=tuple(raw_ad_structures),
    )


def iter_ad_structures(payload: bytes):
    offset = 0
    payload_len = len(payload)

    while offset < payload_len:
        length = payload[offset]
        offset += 1

        if length == 0:
            break

        end = offset + length
        if end > payload_len:
            break

        ad_type = payload[offset]
        data = payload[offset + 1 : end]
        yield ad_type, data
        offset = end


def _parse_uuid16_list(data: bytes) -> list[str]:
    return [_uuid16_to_str(data[idx : idx + 2]) for idx in range(0, len(data) - 1, 2)]


def _parse_uuid32_list(data: bytes) -> list[str]:
    return [_uuid32_to_str(data[idx : idx + 4]) for idx in range(0, len(data) - 3, 4)]


def _parse_uuid128_list(data: bytes) -> list[str]:
    return [_uuid128_to_str(data[idx : idx + 16]) for idx in range(0, len(data) - 15, 16)]


def _uuid16_to_str(raw: bytes) -> str:
    value = int.from_bytes(raw, "little")
    return f"0000{value:04x}-0000-1000-8000-00805f9b34fb"


def _uuid32_to_str(raw: bytes) -> str:
    value = int.from_bytes(raw, "little")
    return f"{value:08x}-0000-1000-8000-00805f9b34fb"


def _uuid128_to_str(raw: bytes) -> str:
    return str(UUID(bytes_le=raw))
