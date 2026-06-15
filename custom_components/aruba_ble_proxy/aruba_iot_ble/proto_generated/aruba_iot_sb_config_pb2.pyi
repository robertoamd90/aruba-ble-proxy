from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TransportConfig(_message.Message):
    __slots__ = ("reportingPeriod", "cellSize")
    REPORTINGPERIOD_FIELD_NUMBER: _ClassVar[int]
    CELLSIZE_FIELD_NUMBER: _ClassVar[int]
    reportingPeriod: int
    cellSize: int
    def __init__(self, reportingPeriod: _Optional[int] = ..., cellSize: _Optional[int] = ...) -> None: ...
