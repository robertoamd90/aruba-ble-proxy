from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class deviceClassEnum(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    unclassified: _ClassVar[deviceClassEnum]
    arubaBeacon: _ClassVar[deviceClassEnum]
    arubaTag: _ClassVar[deviceClassEnum]
    zfTag: _ClassVar[deviceClassEnum]
    stanleyTag: _ClassVar[deviceClassEnum]
    virginBeacon: _ClassVar[deviceClassEnum]
    enoceanSensor: _ClassVar[deviceClassEnum]
    enoceanSwitch: _ClassVar[deviceClassEnum]
    iBeacon: _ClassVar[deviceClassEnum]
    allBleData: _ClassVar[deviceClassEnum]
    RawBleData: _ClassVar[deviceClassEnum]
    eddystone: _ClassVar[deviceClassEnum]
    assaAbloy: _ClassVar[deviceClassEnum]
    arubaSensor: _ClassVar[deviceClassEnum]
    abbSensor: _ClassVar[deviceClassEnum]
    wifiTag: _ClassVar[deviceClassEnum]
    wifiAssocSta: _ClassVar[deviceClassEnum]
    wifiUnassocSta: _ClassVar[deviceClassEnum]
    mysphera: _ClassVar[deviceClassEnum]
    sBeacon: _ClassVar[deviceClassEnum]
    wiliot: _ClassVar[deviceClassEnum]
    ZSD: _ClassVar[deviceClassEnum]
    serialdata: _ClassVar[deviceClassEnum]
    exposureNotification: _ClassVar[deviceClassEnum]
    onity: _ClassVar[deviceClassEnum]
    minew: _ClassVar[deviceClassEnum]
    google: _ClassVar[deviceClassEnum]
    polestar: _ClassVar[deviceClassEnum]
    blyott: _ClassVar[deviceClassEnum]
    diract: _ClassVar[deviceClassEnum]
    gwahygiene: _ClassVar[deviceClassEnum]
    noneBleData: _ClassVar[deviceClassEnum]

class ActionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    bleConnect: _ClassVar[ActionType]
    bleDisconnect: _ClassVar[ActionType]
    gattRead: _ClassVar[ActionType]
    gattWrite: _ClassVar[ActionType]
    gattWriteWithResponse: _ClassVar[ActionType]
    gattNotification: _ClassVar[ActionType]
    gattIndication: _ClassVar[ActionType]
    bleAuthenticate: _ClassVar[ActionType]
    bleEncrypt: _ClassVar[ActionType]

class NbTopic(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    telemetry: _ClassVar[NbTopic]
    actionResults: _ClassVar[NbTopic]
    characteristics: _ClassVar[NbTopic]
    bleData: _ClassVar[NbTopic]
    wifiData: _ClassVar[NbTopic]
    deviceCount: _ClassVar[NbTopic]
    status: _ClassVar[NbTopic]
    zbNbData: _ClassVar[NbTopic]
    serialDataNb: _ClassVar[NbTopic]
    apHealthUpdate: _ClassVar[NbTopic]

class SbTopic(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    actions: _ClassVar[SbTopic]
    config: _ClassVar[SbTopic]
    sbStatus: _ClassVar[SbTopic]
    zbSbData: _ClassVar[SbTopic]
    serialDataSb: _ClassVar[SbTopic]
unclassified: deviceClassEnum
arubaBeacon: deviceClassEnum
arubaTag: deviceClassEnum
zfTag: deviceClassEnum
stanleyTag: deviceClassEnum
virginBeacon: deviceClassEnum
enoceanSensor: deviceClassEnum
enoceanSwitch: deviceClassEnum
iBeacon: deviceClassEnum
allBleData: deviceClassEnum
RawBleData: deviceClassEnum
eddystone: deviceClassEnum
assaAbloy: deviceClassEnum
arubaSensor: deviceClassEnum
abbSensor: deviceClassEnum
wifiTag: deviceClassEnum
wifiAssocSta: deviceClassEnum
wifiUnassocSta: deviceClassEnum
mysphera: deviceClassEnum
sBeacon: deviceClassEnum
wiliot: deviceClassEnum
ZSD: deviceClassEnum
serialdata: deviceClassEnum
exposureNotification: deviceClassEnum
onity: deviceClassEnum
minew: deviceClassEnum
google: deviceClassEnum
polestar: deviceClassEnum
blyott: deviceClassEnum
diract: deviceClassEnum
gwahygiene: deviceClassEnum
noneBleData: deviceClassEnum
bleConnect: ActionType
bleDisconnect: ActionType
gattRead: ActionType
gattWrite: ActionType
gattWriteWithResponse: ActionType
gattNotification: ActionType
gattIndication: ActionType
bleAuthenticate: ActionType
bleEncrypt: ActionType
telemetry: NbTopic
actionResults: NbTopic
characteristics: NbTopic
bleData: NbTopic
wifiData: NbTopic
deviceCount: NbTopic
status: NbTopic
zbNbData: NbTopic
serialDataNb: NbTopic
apHealthUpdate: NbTopic
actions: SbTopic
config: SbTopic
sbStatus: SbTopic
zbSbData: SbTopic
serialDataSb: SbTopic

class BleBondingKey(_message.Message):
    __slots__ = ("key",)
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: bytes
    def __init__(self, key: _Optional[bytes] = ...) -> None: ...

class Meta(_message.Message):
    __slots__ = ("version", "access_token", "nbTopic", "sbTopic")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    ACCESS_TOKEN_FIELD_NUMBER: _ClassVar[int]
    NBTOPIC_FIELD_NUMBER: _ClassVar[int]
    SBTOPIC_FIELD_NUMBER: _ClassVar[int]
    version: int
    access_token: str
    nbTopic: NbTopic
    sbTopic: SbTopic
    def __init__(self, version: _Optional[int] = ..., access_token: _Optional[str] = ..., nbTopic: _Optional[_Union[NbTopic, str]] = ..., sbTopic: _Optional[_Union[SbTopic, str]] = ...) -> None: ...
