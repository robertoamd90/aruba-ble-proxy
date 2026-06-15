from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class NbSerialData(_message.Message):
    __slots__ = ("nbSerialPayload", "nbDeviceId")
    NBSERIALPAYLOAD_FIELD_NUMBER: _ClassVar[int]
    NBDEVICEID_FIELD_NUMBER: _ClassVar[int]
    nbSerialPayload: bytes
    nbDeviceId: str
    def __init__(self, nbSerialPayload: _Optional[bytes] = ..., nbDeviceId: _Optional[str] = ...) -> None: ...
