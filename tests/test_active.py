from custom_components.aruba_ble_proxy.active import (
    ACTION_BLE_CONNECT,
    ACTION_GATT_NOTIFICATION,
    ACTION_GATT_READ,
    ArubaBleActionRequest,
    encode_action_message,
    uuid_to_bytes,
)
import pytest

from custom_components.aruba_ble_proxy.active_client import (
    _raise_for_failed_action,
    aruba_properties_to_bleak,
)
from custom_components.aruba_ble_proxy.aruba_proto import ArubaTelemetryDecoder, _load_aruba_pb2
from custom_components.aruba_ble_proxy.models import ArubaActionStatus, ArubaDeviceStatus


def test_encode_action_message_targets_single_ap():
    _load_aruba_pb2()
    import aruba_iot_sb_pb2
    import aruba_iot_types_pb2

    payload = encode_action_message(
        access_token="secret",
        ap_mac="02:00:00:00:00:01",
        actions=[
            ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                action_id="connect-1",
                device_mac="02:00:00:00:01:01",
                timeout=20,
            )
        ],
    )

    message = aruba_iot_sb_pb2.IotSbMessage()
    message.ParseFromString(payload)

    assert message.meta.version == 1
    assert message.meta.access_token == "secret"
    assert message.meta.sbTopic == aruba_iot_types_pb2.actions
    assert message.receiver.all is False
    assert message.receiver.apMac == bytes.fromhex("020000000001")
    assert len(message.actions) == 1
    assert message.actions[0].type == aruba_iot_types_pb2.bleConnect
    assert message.actions[0].actionId == "connect-1"
    assert message.actions[0].deviceMac == bytes.fromhex("020000000101")


def test_encode_gatt_read_accepts_short_uuid():
    _load_aruba_pb2()
    import aruba_iot_sb_pb2
    import aruba_iot_types_pb2

    payload = encode_action_message(
        access_token=None,
        ap_mac="02:00:00:00:00:01",
        actions=[
            ArubaBleActionRequest(
                action_type=ACTION_GATT_READ,
                action_id="read-1",
                device_mac="02:00:00:00:01:01",
                service_uuid="180f",
                characteristic_uuid="2a19",
            )
        ],
    )

    message = aruba_iot_sb_pb2.IotSbMessage()
    message.ParseFromString(payload)

    assert message.actions[0].type == aruba_iot_types_pb2.gattRead
    assert message.actions[0].serviceUuid == uuid_to_bytes("0000180f-0000-1000-8000-00805f9b34fb")
    assert message.actions[0].characteristicUuid == uuid_to_bytes("00002a19-0000-1000-8000-00805f9b34fb")


def test_encode_gatt_notification_carries_enable_value():
    _load_aruba_pb2()
    import aruba_iot_sb_pb2
    import aruba_iot_types_pb2

    payload = encode_action_message(
        access_token=None,
        ap_mac="02:00:00:00:00:01",
        actions=[
            ArubaBleActionRequest(
                action_type=ACTION_GATT_NOTIFICATION,
                action_id="notify-1",
                device_mac="02:00:00:00:01:01",
                service_uuid="180f",
                characteristic_uuid="2a19",
                value=b"\x01",
            )
        ],
    )

    message = aruba_iot_sb_pb2.IotSbMessage()
    message.ParseFromString(payload)

    assert message.actions[0].type == aruba_iot_types_pb2.gattNotification
    assert message.actions[0].value == b"\x01"


def test_decoder_reads_action_results_and_characteristics():
    _load_aruba_pb2()
    import aruba_iot_nb_pb2
    import aruba_iot_nb_action_results_pb2
    import aruba_iot_nb_characteristic_pb2
    import aruba_iot_types_pb2

    telemetry = aruba_iot_nb_pb2.Telemetry()
    telemetry.meta.version = 1
    telemetry.meta.access_token = "secret"
    telemetry.meta.nbTopic = aruba_iot_types_pb2.actionResults
    telemetry.reporter.mac = bytes.fromhex("020000000001")

    result = telemetry.results.add()
    result.actionId = "read-1"
    result.type = aruba_iot_types_pb2.gattRead
    result.deviceMac = bytes.fromhex("020000000101")
    result.status = aruba_iot_nb_action_results_pb2.success
    result.statusString = "ok"

    characteristic = telemetry.characteristics.add()
    characteristic.deviceMac = bytes.fromhex("020000000101")
    characteristic.serviceUuid = bytes.fromhex("0000180f00001000800000805f9b34fb")
    characteristic.characteristicUuid = bytes.fromhex("00002a1900001000800000805f9b34fb")
    characteristic.value = b"\x64"
    characteristic.properties.append(aruba_iot_nb_characteristic_pb2.read)

    decoded = ArubaTelemetryDecoder(access_token="secret").decode_message(
        telemetry.SerializeToString()
    )

    assert decoded.events == []
    assert decoded.action_results[0].action_id == "read-1"
    assert decoded.action_results[0].status is ArubaActionStatus.SUCCESS
    assert decoded.action_results[0].status_name == "success"
    assert decoded.action_results[0].device_mac == "02:00:00:00:01:01"
    assert decoded.characteristics[0].service_uuid == "0000180f-0000-1000-8000-00805f9b34fb"
    assert decoded.characteristics[0].characteristic_uuid == "00002a19-0000-1000-8000-00805f9b34fb"
    assert decoded.characteristics[0].value == b"\x64"
    assert decoded.characteristics[0].properties == ("read",)


def test_decoder_reads_active_status_update():
    _load_aruba_pb2()
    import aruba_iot_nb_pb2
    import aruba_iot_nb_status_pb2
    import aruba_iot_types_pb2

    telemetry = aruba_iot_nb_pb2.Telemetry()
    telemetry.meta.version = 1
    telemetry.meta.access_token = "secret"
    telemetry.meta.nbTopic = aruba_iot_types_pb2.status
    telemetry.reporter.mac = bytes.fromhex("020000000001")
    telemetry.status.deviceMac = bytes.fromhex("020000000101")
    telemetry.status.status = aruba_iot_nb_status_pb2.inactivityTimeout
    telemetry.status.statusString = "idle timeout"
    telemetry.status.connUpdate.mtu_value = 185

    decoded = ArubaTelemetryDecoder(access_token="secret").decode_message(
        telemetry.SerializeToString()
    )

    assert decoded.statuses
    assert decoded.statuses[0].device_mac == "02:00:00:00:01:01"
    assert decoded.statuses[0].status is ArubaDeviceStatus.INACTIVITY_TIMEOUT
    assert decoded.statuses[0].status_name == "inactivityTimeout"
    assert decoded.statuses[0].status_string == "idle timeout"
    assert decoded.statuses[0].mtu == 185


def test_aruba_properties_to_bleak_names():
    assert aruba_properties_to_bleak(
        ("read", "writeWithoutResponse", "writeWithResponse", "notify", "read")
    ) == ["read", "write-without-response", "write", "notify"]


def test_active_client_accepts_local_notify_success_statuses():
    _raise_for_failed_action({"sent": False, "status": "callbacks_remaining"}, RuntimeError)


def test_active_client_rejects_local_notify_state_mismatch():
    with pytest.raises(RuntimeError, match="not_registered"):
        _raise_for_failed_action({"sent": False, "status": "not_registered"}, RuntimeError)


def test_active_client_rejects_timed_out_action_result():
    with pytest.raises(RuntimeError, match="timeout_waiting_for_action_result"):
        _raise_for_failed_action(
            {
                "sent": True,
                "result": {
                    "received": False,
                    "status": "timeout_waiting_for_action_result",
                },
            },
            RuntimeError,
        )
