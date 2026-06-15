from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CharProperty(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    broadcast: _ClassVar[CharProperty]
    read: _ClassVar[CharProperty]
    writeWithoutResponse: _ClassVar[CharProperty]
    writeWithResponse: _ClassVar[CharProperty]
    notify: _ClassVar[CharProperty]
    indicate: _ClassVar[CharProperty]
    signedWrite: _ClassVar[CharProperty]
    writeReliable: _ClassVar[CharProperty]
    writeAux: _ClassVar[CharProperty]
broadcast: CharProperty
read: CharProperty
writeWithoutResponse: CharProperty
writeWithResponse: CharProperty
notify: CharProperty
indicate: CharProperty
signedWrite: CharProperty
writeReliable: CharProperty
writeAux: CharProperty

class Characteristic(_message.Message):
    __slots__ = ("deviceMac", "serviceUuid", "characteristicUuid", "value", "description", "properties")
    DEVICEMAC_FIELD_NUMBER: _ClassVar[int]
    SERVICEUUID_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICUUID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    deviceMac: bytes
    serviceUuid: bytes
    characteristicUuid: bytes
    value: bytes
    description: str
    properties: _containers.RepeatedScalarFieldContainer[CharProperty]
    def __init__(self, deviceMac: _Optional[bytes] = ..., serviceUuid: _Optional[bytes] = ..., characteristicUuid: _Optional[bytes] = ..., value: _Optional[bytes] = ..., description: _Optional[str] = ..., properties: _Optional[_Iterable[_Union[CharProperty, str]]] = ...) -> None: ...
