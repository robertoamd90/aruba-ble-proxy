from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .models import ArubaBleEvent, BleFrameType


CONNECTABLE_FRAME_TYPES = {
    BleFrameType.ADV_IND,
    BleFrameType.ADV_DIRECT_IND,
}


@dataclass(frozen=True)
class BluetoothPayload:
    name: str
    address: str
    rssi: int
    manufacturer_data: dict[int, bytes]
    service_data: dict[str, bytes]
    service_uuids: list[str]
    source: str
    connectable: bool
    time: float
    tx_power: int | None
    raw: bytes


def event_to_bluetooth_payload(event: ArubaBleEvent) -> BluetoothPayload:
    advertisement = event.advertisement
    return BluetoothPayload(
        name=advertisement.local_name or event.address,
        address=event.address.upper(),
        rssi=event.rssi,
        manufacturer_data=dict(advertisement.manufacturer_data),
        service_data=dict(advertisement.service_data),
        service_uuids=list(advertisement.service_uuids),
        source=event.source.upper(),
        connectable=_is_connectable_frame(event.frame_type),
        time=monotonic(),
        tx_power=advertisement.tx_power,
        raw=event.payload,
    )


def _is_connectable_frame(frame_type: BleFrameType | int) -> bool:
    return frame_type in CONNECTABLE_FRAME_TYPES
