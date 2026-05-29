import aruba_iot_zb_types_pb2 as _aruba_iot_zb_types_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ZbNbReport(_message.Message):
    __slots__ = ("mac", "e2pc", "payload")
    MAC_FIELD_NUMBER: _ClassVar[int]
    E2PC_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    mac: bytes
    e2pc: _aruba_iot_zb_types_pb2.ZbE2PC
    payload: bytes
    def __init__(self, mac: _Optional[bytes] = ..., e2pc: _Optional[_Union[_aruba_iot_zb_types_pb2.ZbE2PC, _Mapping]] = ..., payload: _Optional[bytes] = ...) -> None: ...

class ZbNbAck(_message.Message):
    __slots__ = ("reqid", "result", "code")
    REQID_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    result: _aruba_iot_zb_types_pb2.ZbResult
    code: _aruba_iot_zb_types_pb2.ZbAckCode
    def __init__(self, reqid: _Optional[str] = ..., result: _Optional[_Union[_aruba_iot_zb_types_pb2.ZbResult, str]] = ..., code: _Optional[_Union[_aruba_iot_zb_types_pb2.ZbAckCode, str]] = ...) -> None: ...

class ZbNbRsp(_message.Message):
    __slots__ = ("reqid",)
    REQID_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    def __init__(self, reqid: _Optional[str] = ...) -> None: ...

class NbZbMsg(_message.Message):
    __slots__ = ("radio_mac", "report", "ack", "response")
    RADIO_MAC_FIELD_NUMBER: _ClassVar[int]
    REPORT_FIELD_NUMBER: _ClassVar[int]
    ACK_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    radio_mac: bytes
    report: ZbNbReport
    ack: ZbNbAck
    response: ZbNbRsp
    def __init__(self, radio_mac: _Optional[bytes] = ..., report: _Optional[_Union[ZbNbReport, _Mapping]] = ..., ack: _Optional[_Union[ZbNbAck, _Mapping]] = ..., response: _Optional[_Union[ZbNbRsp, _Mapping]] = ...) -> None: ...
