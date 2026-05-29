from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ConnectCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    statusOK: _ClassVar[ConnectCode]
    tokenExpire: _ClassVar[ConnectCode]
statusOK: ConnectCode
tokenExpire: ConnectCode

class ConnectStatus(_message.Message):
    __slots__ = ("connectCode", "connectDescription")
    CONNECTCODE_FIELD_NUMBER: _ClassVar[int]
    CONNECTDESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    connectCode: ConnectCode
    connectDescription: str
    def __init__(self, connectCode: _Optional[_Union[ConnectCode, str]] = ..., connectDescription: _Optional[str] = ...) -> None: ...
