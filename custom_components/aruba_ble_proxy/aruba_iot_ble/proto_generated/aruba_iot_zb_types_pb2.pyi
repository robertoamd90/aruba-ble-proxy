import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ZbResult(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SUCCEEDED: _ClassVar[ZbResult]
    FAILED: _ClassVar[ZbResult]

class ZbAckCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OK: _ClassVar[ZbAckCode]
SUCCEEDED: ZbResult
FAILED: ZbResult
OK: ZbAckCode

class ZbEPC(_message.Message):
    __slots__ = ("endpoint", "profile_id", "cluster_id")
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    PROFILE_ID_FIELD_NUMBER: _ClassVar[int]
    CLUSTER_ID_FIELD_NUMBER: _ClassVar[int]
    endpoint: int
    profile_id: int
    cluster_id: int
    def __init__(self, endpoint: _Optional[int] = ..., profile_id: _Optional[int] = ..., cluster_id: _Optional[int] = ...) -> None: ...

class ZbE2PC(_message.Message):
    __slots__ = ("destination", "source_endpoint")
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    destination: ZbEPC
    source_endpoint: int
    def __init__(self, destination: _Optional[_Union[ZbEPC, _Mapping]] = ..., source_endpoint: _Optional[int] = ...) -> None: ...
