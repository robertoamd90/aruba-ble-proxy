import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AuthenticationMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    none: _ClassVar[AuthenticationMethod]
    passkey: _ClassVar[AuthenticationMethod]
    oob: _ClassVar[AuthenticationMethod]
    lescNone: _ClassVar[AuthenticationMethod]
    lescPasskey: _ClassVar[AuthenticationMethod]
    lescOob: _ClassVar[AuthenticationMethod]
none: AuthenticationMethod
passkey: AuthenticationMethod
oob: AuthenticationMethod
lescNone: AuthenticationMethod
lescPasskey: AuthenticationMethod
lescOob: AuthenticationMethod

class Authentication(_message.Message):
    __slots__ = ("method", "bonding", "passkey", "keyOob", "keyOwn")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    BONDING_FIELD_NUMBER: _ClassVar[int]
    PASSKEY_FIELD_NUMBER: _ClassVar[int]
    KEYOOB_FIELD_NUMBER: _ClassVar[int]
    KEYOWN_FIELD_NUMBER: _ClassVar[int]
    method: AuthenticationMethod
    bonding: bool
    passkey: str
    keyOob: bytes
    keyOwn: bytes
    def __init__(self, method: _Optional[_Union[AuthenticationMethod, str]] = ..., bonding: bool = ..., passkey: _Optional[str] = ..., keyOob: _Optional[bytes] = ..., keyOwn: _Optional[bytes] = ...) -> None: ...

class Action(_message.Message):
    __slots__ = ("actionId", "type", "deviceMac", "serviceUuid", "characteristicUuid", "timeOut", "value", "authentication", "bondingKey", "apbMac")
    ACTIONID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DEVICEMAC_FIELD_NUMBER: _ClassVar[int]
    SERVICEUUID_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICUUID_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    AUTHENTICATION_FIELD_NUMBER: _ClassVar[int]
    BONDINGKEY_FIELD_NUMBER: _ClassVar[int]
    APBMAC_FIELD_NUMBER: _ClassVar[int]
    actionId: str
    type: _aruba_iot_types_pb2.ActionType
    deviceMac: bytes
    serviceUuid: bytes
    characteristicUuid: bytes
    timeOut: int
    value: bytes
    authentication: Authentication
    bondingKey: _aruba_iot_types_pb2.BleBondingKey
    apbMac: bytes
    def __init__(self, actionId: _Optional[str] = ..., type: _Optional[_Union[_aruba_iot_types_pb2.ActionType, str]] = ..., deviceMac: _Optional[bytes] = ..., serviceUuid: _Optional[bytes] = ..., characteristicUuid: _Optional[bytes] = ..., timeOut: _Optional[int] = ..., value: _Optional[bytes] = ..., authentication: _Optional[_Union[Authentication, _Mapping]] = ..., bondingKey: _Optional[_Union[_aruba_iot_types_pb2.BleBondingKey, _Mapping]] = ..., apbMac: _Optional[bytes] = ...) -> None: ...
