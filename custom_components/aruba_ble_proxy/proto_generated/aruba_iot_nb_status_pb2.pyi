from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class statusValue(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    deviceDisconnected: _ClassVar[statusValue]
    inactivityTimeout: _ClassVar[statusValue]
    connectionUpdate: _ClassVar[statusValue]
deviceDisconnected: statusValue
inactivityTimeout: statusValue
connectionUpdate: statusValue

class ConnUpdate(_message.Message):
    __slots__ = ("mtu_value",)
    MTU_VALUE_FIELD_NUMBER: _ClassVar[int]
    mtu_value: int
    def __init__(self, mtu_value: _Optional[int] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("deviceMac", "status", "statusString", "connUpdate")
    DEVICEMAC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUSSTRING_FIELD_NUMBER: _ClassVar[int]
    CONNUPDATE_FIELD_NUMBER: _ClassVar[int]
    deviceMac: bytes
    status: statusValue
    statusString: str
    connUpdate: ConnUpdate
    def __init__(self, deviceMac: _Optional[bytes] = ..., status: _Optional[_Union[statusValue, str]] = ..., statusString: _Optional[str] = ..., connUpdate: _Optional[_Union[ConnUpdate, _Mapping]] = ...) -> None: ...
