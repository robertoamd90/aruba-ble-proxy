from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HealthStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    healthy: _ClassVar[HealthStatus]
    degraded: _ClassVar[HealthStatus]
    unavailable: _ClassVar[HealthStatus]

class IotRadioFirmware(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    arubaDefault: _ClassVar[IotRadioFirmware]

class IotRadioType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    gen1: _ClassVar[IotRadioType]
    gen2: _ClassVar[IotRadioType]
healthy: HealthStatus
degraded: HealthStatus
unavailable: HealthStatus
arubaDefault: IotRadioFirmware
gen1: IotRadioType
gen2: IotRadioType

class IotRadio(_message.Message):
    __slots__ = ("mac", "hardware", "firmware", "health", "external")
    MAC_FIELD_NUMBER: _ClassVar[int]
    HARDWARE_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_FIELD_NUMBER: _ClassVar[int]
    HEALTH_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_FIELD_NUMBER: _ClassVar[int]
    mac: bytes
    hardware: IotRadioType
    firmware: IotRadioFirmware
    health: HealthStatus
    external: bool
    def __init__(self, mac: _Optional[bytes] = ..., hardware: _Optional[_Union[IotRadioType, str]] = ..., firmware: _Optional[_Union[IotRadioFirmware, str]] = ..., health: _Optional[_Union[HealthStatus, str]] = ..., external: bool = ...) -> None: ...

class UsbDevice(_message.Message):
    __slots__ = ("identifier", "health")
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    HEALTH_FIELD_NUMBER: _ClassVar[int]
    identifier: str
    health: HealthStatus
    def __init__(self, identifier: _Optional[str] = ..., health: _Optional[_Union[HealthStatus, str]] = ...) -> None: ...

class ApHealthUpdate(_message.Message):
    __slots__ = ("apStatus", "radio", "usb")
    APSTATUS_FIELD_NUMBER: _ClassVar[int]
    RADIO_FIELD_NUMBER: _ClassVar[int]
    USB_FIELD_NUMBER: _ClassVar[int]
    apStatus: HealthStatus
    radio: _containers.RepeatedCompositeFieldContainer[IotRadio]
    usb: _containers.RepeatedCompositeFieldContainer[UsbDevice]
    def __init__(self, apStatus: _Optional[_Union[HealthStatus, str]] = ..., radio: _Optional[_Iterable[_Union[IotRadio, _Mapping]]] = ..., usb: _Optional[_Iterable[_Union[UsbDevice, _Mapping]]] = ...) -> None: ...
