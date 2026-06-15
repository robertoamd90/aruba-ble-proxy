from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ACTION_BLE_CONNECT = "bleConnect"
ACTION_BLE_DISCONNECT = "bleDisconnect"
ACTION_GATT_READ = "gattRead"
ACTION_GATT_WRITE = "gattWrite"
ACTION_GATT_WRITE_WITH_RESPONSE = "gattWriteWithResponse"
ACTION_GATT_NOTIFICATION = "gattNotification"
ACTION_GATT_INDICATION = "gattIndication"

SUPPORTED_ACTIONS = {
    ACTION_BLE_CONNECT,
    ACTION_BLE_DISCONNECT,
    ACTION_GATT_READ,
    ACTION_GATT_WRITE,
    ACTION_GATT_WRITE_WITH_RESPONSE,
    ACTION_GATT_NOTIFICATION,
    ACTION_GATT_INDICATION,
}


@dataclass(frozen=True)
class ArubaBleActionRequest:
    action_type: str
    device_mac: str
    action_id: str | None = None
    service_uuid: str | None = None
    characteristic_uuid: str | None = None
    value: bytes | None = None
    timeout: int = 20
    apb_mac: str | None = None

    def with_action_id(self) -> "ArubaBleActionRequest":
        if self.action_id:
            return self
        return ArubaBleActionRequest(
            action_type=self.action_type,
            device_mac=self.device_mac,
            action_id=uuid.uuid4().hex,
            service_uuid=self.service_uuid,
            characteristic_uuid=self.characteristic_uuid,
            value=self.value,
            timeout=self.timeout,
            apb_mac=self.apb_mac,
        )


def encode_action_message(
    *,
    access_token: str | None,
    ap_mac: str,
    actions: list[ArubaBleActionRequest],
) -> bytes:
    pb = _load_sb_pb2()
    message = pb["sb"].IotSbMessage()
    message.meta.version = 1
    message.meta.sbTopic = pb["types"].actions
    if access_token:
        message.meta.access_token = access_token
    message.receiver.all = False
    message.receiver.apMac = mac_to_bytes(ap_mac)

    for request in actions:
        _append_action(message.actions.add(), request, pb["types"])

    return message.SerializeToString()


def mac_to_bytes(value: str) -> bytes:
    cleaned = value.strip().replace(":", "").replace("-", "")
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address: {value}")
    return bytes.fromhex(cleaned)


def uuid_to_bytes(value: str | None) -> bytes:
    if value is None:
        return b""
    cleaned = value.strip().replace("-", "")
    if len(cleaned) == 4:
        cleaned = f"0000{cleaned}00001000800000805f9b34fb"
    if len(cleaned) != 32:
        raise ValueError(f"Invalid BLE UUID: {value}")
    return bytes.fromhex(cleaned)


def _append_action(action: Any, request: ArubaBleActionRequest, types_pb2: Any) -> None:
    request = request.with_action_id()
    if request.action_type not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported Aruba BLE action: {request.action_type}")

    action.actionId = request.action_id or uuid.uuid4().hex
    action.type = getattr(types_pb2, request.action_type)
    action.deviceMac = mac_to_bytes(request.device_mac)
    action.timeOut = int(request.timeout)
    if request.service_uuid:
        action.serviceUuid = uuid_to_bytes(request.service_uuid)
    if request.characteristic_uuid:
        action.characteristicUuid = uuid_to_bytes(request.characteristic_uuid)
    if request.value is not None:
        action.value = request.value
    if request.apb_mac:
        action.apbMac = mac_to_bytes(request.apb_mac)


def _load_sb_pb2() -> dict[str, Any]:
    generated_proto_dir = Path(__file__).resolve().parent / "proto_generated"
    generated_proto_path = str(generated_proto_dir)
    if generated_proto_path not in sys.path:
        sys.path.insert(0, generated_proto_path)

    import aruba_iot_sb_pb2
    import aruba_iot_types_pb2

    return {"sb": aruba_iot_sb_pb2, "types": aruba_iot_types_pb2}
