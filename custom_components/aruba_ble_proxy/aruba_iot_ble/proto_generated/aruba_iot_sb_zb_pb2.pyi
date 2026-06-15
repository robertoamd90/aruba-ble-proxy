import aruba_iot_zb_types_pb2 as _aruba_iot_zb_types_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ZbSbSend(_message.Message):
    __slots__ = ("reqid", "mac", "e2pc", "payload")
    REQID_FIELD_NUMBER: _ClassVar[int]
    MAC_FIELD_NUMBER: _ClassVar[int]
    E2PC_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    mac: bytes
    e2pc: _aruba_iot_zb_types_pb2.ZbE2PC
    payload: bytes
    def __init__(self, reqid: _Optional[str] = ..., mac: _Optional[bytes] = ..., e2pc: _Optional[_Union[_aruba_iot_zb_types_pb2.ZbE2PC, _Mapping]] = ..., payload: _Optional[bytes] = ...) -> None: ...

class ZbSbRead(_message.Message):
    __slots__ = ("reqid",)
    REQID_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    def __init__(self, reqid: _Optional[str] = ...) -> None: ...

class ZbSbWrite(_message.Message):
    __slots__ = ("reqid",)
    REQID_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    def __init__(self, reqid: _Optional[str] = ...) -> None: ...

class ZbSbAction(_message.Message):
    __slots__ = ("reqid",)
    REQID_FIELD_NUMBER: _ClassVar[int]
    reqid: str
    def __init__(self, reqid: _Optional[str] = ...) -> None: ...

class ZbSbReq(_message.Message):
    __slots__ = ("read", "write", "action")
    READ_FIELD_NUMBER: _ClassVar[int]
    WRITE_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    read: ZbSbRead
    write: ZbSbWrite
    action: ZbSbAction
    def __init__(self, read: _Optional[_Union[ZbSbRead, _Mapping]] = ..., write: _Optional[_Union[ZbSbWrite, _Mapping]] = ..., action: _Optional[_Union[ZbSbAction, _Mapping]] = ...) -> None: ...

class SbZbMsg(_message.Message):
    __slots__ = ("radio_mac", "send", "request")
    RADIO_MAC_FIELD_NUMBER: _ClassVar[int]
    SEND_FIELD_NUMBER: _ClassVar[int]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    radio_mac: bytes
    send: ZbSbSend
    request: ZbSbReq
    def __init__(self, radio_mac: _Optional[bytes] = ..., send: _Optional[_Union[ZbSbSend, _Mapping]] = ..., request: _Optional[_Union[ZbSbReq, _Mapping]] = ...) -> None: ...
