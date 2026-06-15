from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BleFrameType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    adv_ind: _ClassVar[BleFrameType]
    adv_direct_ind: _ClassVar[BleFrameType]
    adv_nonconn_ind: _ClassVar[BleFrameType]
    scan_rsp: _ClassVar[BleFrameType]
    adv_scan_ind: _ClassVar[BleFrameType]

class MacAddrType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    addr_type_public: _ClassVar[MacAddrType]
    addr_type_static: _ClassVar[MacAddrType]
    addr_type_private_non_resolvable: _ClassVar[MacAddrType]
    addr_type_private_resolvable: _ClassVar[MacAddrType]
adv_ind: BleFrameType
adv_direct_ind: BleFrameType
adv_nonconn_ind: BleFrameType
scan_rsp: BleFrameType
adv_scan_ind: BleFrameType
addr_type_public: MacAddrType
addr_type_static: MacAddrType
addr_type_private_non_resolvable: MacAddrType
addr_type_private_resolvable: MacAddrType

class BleData(_message.Message):
    __slots__ = ("mac", "frameType", "data", "rssi", "addrType", "apbMac")
    MAC_FIELD_NUMBER: _ClassVar[int]
    FRAMETYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    ADDRTYPE_FIELD_NUMBER: _ClassVar[int]
    APBMAC_FIELD_NUMBER: _ClassVar[int]
    mac: bytes
    frameType: BleFrameType
    data: bytes
    rssi: int
    addrType: MacAddrType
    apbMac: bytes
    def __init__(self, mac: _Optional[bytes] = ..., frameType: _Optional[_Union[BleFrameType, str]] = ..., data: _Optional[bytes] = ..., rssi: _Optional[int] = ..., addrType: _Optional[_Union[MacAddrType, str]] = ..., apbMac: _Optional[bytes] = ...) -> None: ...
