from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class SbSerialData(_message.Message):
    __slots__ = ("sbDeviceId", "sbSerialPayload")
    SBDEVICEID_FIELD_NUMBER: _ClassVar[int]
    SBSERIALPAYLOAD_FIELD_NUMBER: _ClassVar[int]
    sbDeviceId: str
    sbSerialPayload: bytes
    def __init__(self, sbDeviceId: _Optional[str] = ..., sbSerialPayload: _Optional[bytes] = ...) -> None: ...
