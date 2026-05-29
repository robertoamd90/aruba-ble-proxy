import aruba_iot_types_pb2 as _aruba_iot_types_pb2
import aruba_iot_sb_action_pb2 as _aruba_iot_sb_action_pb2
import aruba_iot_sb_config_pb2 as _aruba_iot_sb_config_pb2
import aruba_iot_sb_status_pb2 as _aruba_iot_sb_status_pb2
import aruba_iot_sb_zb_pb2 as _aruba_iot_sb_zb_pb2
import aruba_iot_sb_serial_data_pb2 as _aruba_iot_sb_serial_data_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Receiver(_message.Message):
    __slots__ = ("all", "apMac")
    ALL_FIELD_NUMBER: _ClassVar[int]
    APMAC_FIELD_NUMBER: _ClassVar[int]
    all: bool
    apMac: bytes
    def __init__(self, all: bool = ..., apMac: _Optional[bytes] = ...) -> None: ...

class IotSbMessage(_message.Message):
    __slots__ = ("meta", "receiver", "actions", "config", "status", "zigbee", "sbSData")
    META_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ZIGBEE_FIELD_NUMBER: _ClassVar[int]
    SBSDATA_FIELD_NUMBER: _ClassVar[int]
    meta: _aruba_iot_types_pb2.Meta
    receiver: Receiver
    actions: _containers.RepeatedCompositeFieldContainer[_aruba_iot_sb_action_pb2.Action]
    config: _aruba_iot_sb_config_pb2.TransportConfig
    status: _aruba_iot_sb_status_pb2.ConnectStatus
    zigbee: _aruba_iot_sb_zb_pb2.SbZbMsg
    sbSData: _containers.RepeatedCompositeFieldContainer[_aruba_iot_sb_serial_data_pb2.SbSerialData]
    def __init__(self, meta: _Optional[_Union[_aruba_iot_types_pb2.Meta, _Mapping]] = ..., receiver: _Optional[_Union[Receiver, _Mapping]] = ..., actions: _Optional[_Iterable[_Union[_aruba_iot_sb_action_pb2.Action, _Mapping]]] = ..., config: _Optional[_Union[_aruba_iot_sb_config_pb2.TransportConfig, _Mapping]] = ..., status: _Optional[_Union[_aruba_iot_sb_status_pb2.ConnectStatus, _Mapping]] = ..., zigbee: _Optional[_Union[_aruba_iot_sb_zb_pb2.SbZbMsg, _Mapping]] = ..., sbSData: _Optional[_Iterable[_Union[_aruba_iot_sb_serial_data_pb2.SbSerialData, _Mapping]]] = ...) -> None: ...
