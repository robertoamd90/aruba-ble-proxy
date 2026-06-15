import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class DeviceCount(_message.Message):
    __slots__ = ("dev_unclassified", "dev_arubaBeacon", "dev_arubaTag", "dev_zfTag", "dev_stanleyTag", "dev_virginBeacon", "dev_enoceanSensor", "dev_enoceanSwitch", "dev_iBeacon", "dev_allBleData", "dev_RawBleData", "dev_eddystone", "dev_assaAbloy", "dev_arubaSensor", "dev_abbSensor", "dev_wifiTag", "dev_wifiAssocSta", "dev_wifiUnassocSta", "dev_mysphera", "dev_sBeacon", "dev_onity", "dev_minew", "dev_google", "dev_polestar", "dev_blyott", "dev_diract", "dev_gwahygiene")
    DEV_UNCLASSIFIED_FIELD_NUMBER: _ClassVar[int]
    DEV_ARUBABEACON_FIELD_NUMBER: _ClassVar[int]
    DEV_ARUBATAG_FIELD_NUMBER: _ClassVar[int]
    DEV_ZFTAG_FIELD_NUMBER: _ClassVar[int]
    DEV_STANLEYTAG_FIELD_NUMBER: _ClassVar[int]
    DEV_VIRGINBEACON_FIELD_NUMBER: _ClassVar[int]
    DEV_ENOCEANSENSOR_FIELD_NUMBER: _ClassVar[int]
    DEV_ENOCEANSWITCH_FIELD_NUMBER: _ClassVar[int]
    DEV_IBEACON_FIELD_NUMBER: _ClassVar[int]
    DEV_ALLBLEDATA_FIELD_NUMBER: _ClassVar[int]
    DEV_RAWBLEDATA_FIELD_NUMBER: _ClassVar[int]
    DEV_EDDYSTONE_FIELD_NUMBER: _ClassVar[int]
    DEV_ASSAABLOY_FIELD_NUMBER: _ClassVar[int]
    DEV_ARUBASENSOR_FIELD_NUMBER: _ClassVar[int]
    DEV_ABBSENSOR_FIELD_NUMBER: _ClassVar[int]
    DEV_WIFITAG_FIELD_NUMBER: _ClassVar[int]
    DEV_WIFIASSOCSTA_FIELD_NUMBER: _ClassVar[int]
    DEV_WIFIUNASSOCSTA_FIELD_NUMBER: _ClassVar[int]
    DEV_MYSPHERA_FIELD_NUMBER: _ClassVar[int]
    DEV_SBEACON_FIELD_NUMBER: _ClassVar[int]
    DEV_ONITY_FIELD_NUMBER: _ClassVar[int]
    DEV_MINEW_FIELD_NUMBER: _ClassVar[int]
    DEV_GOOGLE_FIELD_NUMBER: _ClassVar[int]
    DEV_POLESTAR_FIELD_NUMBER: _ClassVar[int]
    DEV_BLYOTT_FIELD_NUMBER: _ClassVar[int]
    DEV_DIRACT_FIELD_NUMBER: _ClassVar[int]
    DEV_GWAHYGIENE_FIELD_NUMBER: _ClassVar[int]
    dev_unclassified: int
    dev_arubaBeacon: int
    dev_arubaTag: int
    dev_zfTag: int
    dev_stanleyTag: int
    dev_virginBeacon: int
    dev_enoceanSensor: int
    dev_enoceanSwitch: int
    dev_iBeacon: int
    dev_allBleData: int
    dev_RawBleData: int
    dev_eddystone: int
    dev_assaAbloy: int
    dev_arubaSensor: int
    dev_abbSensor: int
    dev_wifiTag: int
    dev_wifiAssocSta: int
    dev_wifiUnassocSta: int
    dev_mysphera: int
    dev_sBeacon: int
    dev_onity: int
    dev_minew: int
    dev_google: int
    dev_polestar: int
    dev_blyott: int
    dev_diract: int
    dev_gwahygiene: int
    def __init__(self, dev_unclassified: _Optional[int] = ..., dev_arubaBeacon: _Optional[int] = ..., dev_arubaTag: _Optional[int] = ..., dev_zfTag: _Optional[int] = ..., dev_stanleyTag: _Optional[int] = ..., dev_virginBeacon: _Optional[int] = ..., dev_enoceanSensor: _Optional[int] = ..., dev_enoceanSwitch: _Optional[int] = ..., dev_iBeacon: _Optional[int] = ..., dev_allBleData: _Optional[int] = ..., dev_RawBleData: _Optional[int] = ..., dev_eddystone: _Optional[int] = ..., dev_assaAbloy: _Optional[int] = ..., dev_arubaSensor: _Optional[int] = ..., dev_abbSensor: _Optional[int] = ..., dev_wifiTag: _Optional[int] = ..., dev_wifiAssocSta: _Optional[int] = ..., dev_wifiUnassocSta: _Optional[int] = ..., dev_mysphera: _Optional[int] = ..., dev_sBeacon: _Optional[int] = ..., dev_onity: _Optional[int] = ..., dev_minew: _Optional[int] = ..., dev_google: _Optional[int] = ..., dev_polestar: _Optional[int] = ..., dev_blyott: _Optional[int] = ..., dev_diract: _Optional[int] = ..., dev_gwahygiene: _Optional[int] = ...) -> None: ...
