import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActionStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    failureGeneric: _ClassVar[ActionStatus]
    success: _ClassVar[ActionStatus]
    deviceNotFound: _ClassVar[ActionStatus]
    apNotFound: _ClassVar[ActionStatus]
    actionTimeout: _ClassVar[ActionStatus]
    connectionAborted: _ClassVar[ActionStatus]
    authenticationFailed: _ClassVar[ActionStatus]
    notConnected: _ClassVar[ActionStatus]
    previousActionFailed: _ClassVar[ActionStatus]
    alreadyConnected: _ClassVar[ActionStatus]
    noMoreConnectionSlots: _ClassVar[ActionStatus]
    decodingFailed: _ClassVar[ActionStatus]
    characteristicNotFound: _ClassVar[ActionStatus]
    invalidRequest: _ClassVar[ActionStatus]
    gattError: _ClassVar[ActionStatus]
    encryptionFailed: _ClassVar[ActionStatus]
failureGeneric: ActionStatus
success: ActionStatus
deviceNotFound: ActionStatus
apNotFound: ActionStatus
actionTimeout: ActionStatus
connectionAborted: ActionStatus
authenticationFailed: ActionStatus
notConnected: ActionStatus
previousActionFailed: ActionStatus
alreadyConnected: ActionStatus
noMoreConnectionSlots: ActionStatus
decodingFailed: ActionStatus
characteristicNotFound: ActionStatus
invalidRequest: ActionStatus
gattError: ActionStatus
encryptionFailed: ActionStatus

class ActionResult(_message.Message):
    __slots__ = ("actionId", "type", "deviceMac", "status", "statusString", "bondingKey", "apbMac")
    ACTIONID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DEVICEMAC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUSSTRING_FIELD_NUMBER: _ClassVar[int]
    BONDINGKEY_FIELD_NUMBER: _ClassVar[int]
    APBMAC_FIELD_NUMBER: _ClassVar[int]
    actionId: str
    type: _aruba_iot_types_pb2.ActionType
    deviceMac: bytes
    status: ActionStatus
    statusString: str
    bondingKey: _aruba_iot_types_pb2.BleBondingKey
    apbMac: bytes
    def __init__(self, actionId: _Optional[str] = ..., type: _Optional[_Union[_aruba_iot_types_pb2.ActionType, str]] = ..., deviceMac: _Optional[bytes] = ..., status: _Optional[_Union[ActionStatus, str]] = ..., statusString: _Optional[str] = ..., bondingKey: _Optional[_Union[_aruba_iot_types_pb2.BleBondingKey, _Mapping]] = ..., apbMac: _Optional[bytes] = ...) -> None: ...
