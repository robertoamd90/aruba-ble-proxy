import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WiFiData(_message.Message):
    __slots__ = ("mac", "deviceClass", "rssi", "rtls_payload")
    MAC_FIELD_NUMBER: _ClassVar[int]
    DEVICECLASS_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    RTLS_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    mac: bytes
    deviceClass: _containers.RepeatedScalarFieldContainer[_aruba_iot_types_pb2.deviceClassEnum]
    rssi: int
    rtls_payload: bytes
    def __init__(self, mac: _Optional[bytes] = ..., deviceClass: _Optional[_Iterable[_Union[_aruba_iot_types_pb2.deviceClassEnum, str]]] = ..., rssi: _Optional[int] = ..., rtls_payload: _Optional[bytes] = ...) -> None: ...
