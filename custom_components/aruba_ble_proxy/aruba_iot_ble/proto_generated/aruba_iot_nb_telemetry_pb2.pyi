import aruba_iot_types_pb2 as _aruba_iot_types_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class rockerSwitchPosition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    idle: _ClassVar[rockerSwitchPosition]
    topPressed: _ClassVar[rockerSwitchPosition]
    bottomPressed: _ClassVar[rockerSwitchPosition]

class CellEvent(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    entry: _ClassVar[CellEvent]
    exit: _ClassVar[CellEvent]
    update: _ClassVar[CellEvent]
    ageout: _ClassVar[CellEvent]

class AccelStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ok: _ClassVar[AccelStatus]
    outOfRange: _ClassVar[AccelStatus]
    threshold1: _ClassVar[AccelStatus]
    threshold2: _ClassVar[AccelStatus]

class Alarm(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    water: _ClassVar[Alarm]
    smoke: _ClassVar[Alarm]
    fire: _ClassVar[Alarm]
    glassbreak: _ClassVar[Alarm]
    intrusion: _ClassVar[Alarm]

class ContactPosition(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    open: _ClassVar[ContactPosition]
    closed: _ClassVar[ContactPosition]

class MechanicalH(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    upToRight: _ClassVar[MechanicalH]
    rightToDown: _ClassVar[MechanicalH]
    downToLeft: _ClassVar[MechanicalH]
    leftToUp: _ClassVar[MechanicalH]
    upToLeft: _ClassVar[MechanicalH]
    leftToDown: _ClassVar[MechanicalH]
    downToRight: _ClassVar[MechanicalH]
    rightToUp: _ClassVar[MechanicalH]

class switchState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    unknown: _ClassVar[switchState]
    on: _ClassVar[switchState]
    off: _ClassVar[switchState]
idle: rockerSwitchPosition
topPressed: rockerSwitchPosition
bottomPressed: rockerSwitchPosition
entry: CellEvent
exit: CellEvent
update: CellEvent
ageout: CellEvent
ok: AccelStatus
outOfRange: AccelStatus
threshold1: AccelStatus
threshold2: AccelStatus
water: Alarm
smoke: Alarm
fire: Alarm
glassbreak: Alarm
intrusion: Alarm
open: ContactPosition
closed: ContactPosition
upToRight: MechanicalH
rightToDown: MechanicalH
downToLeft: MechanicalH
leftToUp: MechanicalH
upToLeft: MechanicalH
leftToDown: MechanicalH
downToRight: MechanicalH
rightToUp: MechanicalH
unknown: switchState
on: switchState
off: switchState

class Firmware(_message.Message):
    __slots__ = ("version", "bankA", "bankB")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    BANKA_FIELD_NUMBER: _ClassVar[int]
    BANKB_FIELD_NUMBER: _ClassVar[int]
    version: str
    bankA: str
    bankB: str
    def __init__(self, version: _Optional[str] = ..., bankA: _Optional[str] = ..., bankB: _Optional[str] = ...) -> None: ...

class History(_message.Message):
    __slots__ = ("time", "rssi", "rxRadioId", "antenna")
    TIME_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    RXRADIOID_FIELD_NUMBER: _ClassVar[int]
    ANTENNA_FIELD_NUMBER: _ClassVar[int]
    time: int
    rssi: int
    rxRadioId: int
    antenna: int
    def __init__(self, time: _Optional[int] = ..., rssi: _Optional[int] = ..., rxRadioId: _Optional[int] = ..., antenna: _Optional[int] = ...) -> None: ...

class Rssi(_message.Message):
    __slots__ = ("last", "avg", "max", "history", "smooth")
    LAST_FIELD_NUMBER: _ClassVar[int]
    AVG_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    SMOOTH_FIELD_NUMBER: _ClassVar[int]
    last: int
    avg: int
    max: int
    history: _containers.RepeatedCompositeFieldContainer[History]
    smooth: int
    def __init__(self, last: _Optional[int] = ..., avg: _Optional[int] = ..., max: _Optional[int] = ..., history: _Optional[_Iterable[_Union[History, _Mapping]]] = ..., smooth: _Optional[int] = ...) -> None: ...

class BeaconEvent(_message.Message):
    __slots__ = ("event",)
    EVENT_FIELD_NUMBER: _ClassVar[int]
    event: CellEvent
    def __init__(self, event: _Optional[_Union[CellEvent, str]] = ...) -> None: ...

class Cell(_message.Message):
    __slots__ = ("isInside", "distance")
    ISINSIDE_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    isInside: bool
    distance: float
    def __init__(self, isInside: bool = ..., distance: _Optional[float] = ...) -> None: ...

class Ibeacon(_message.Message):
    __slots__ = ("uuid", "major", "minor", "power", "extra")
    UUID_FIELD_NUMBER: _ClassVar[int]
    MAJOR_FIELD_NUMBER: _ClassVar[int]
    MINOR_FIELD_NUMBER: _ClassVar[int]
    POWER_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    uuid: bytes
    major: int
    minor: int
    power: int
    extra: bytes
    def __init__(self, uuid: _Optional[bytes] = ..., major: _Optional[int] = ..., minor: _Optional[int] = ..., power: _Optional[int] = ..., extra: _Optional[bytes] = ...) -> None: ...

class EddyUID(_message.Message):
    __slots__ = ("nid", "bid")
    NID_FIELD_NUMBER: _ClassVar[int]
    BID_FIELD_NUMBER: _ClassVar[int]
    nid: bytes
    bid: bytes
    def __init__(self, nid: _Optional[bytes] = ..., bid: _Optional[bytes] = ...) -> None: ...

class EddyURL(_message.Message):
    __slots__ = ("prefix", "encodedUrl")
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    ENCODEDURL_FIELD_NUMBER: _ClassVar[int]
    prefix: int
    encodedUrl: bytes
    def __init__(self, prefix: _Optional[int] = ..., encodedUrl: _Optional[bytes] = ...) -> None: ...

class Eddystone(_message.Message):
    __slots__ = ("power", "uid", "url")
    POWER_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    power: int
    uid: EddyUID
    url: EddyURL
    def __init__(self, power: _Optional[int] = ..., uid: _Optional[_Union[EddyUID, _Mapping]] = ..., url: _Optional[_Union[EddyURL, _Mapping]] = ...) -> None: ...

class Beacons(_message.Message):
    __slots__ = ("ibeacon", "eddystone")
    IBEACON_FIELD_NUMBER: _ClassVar[int]
    EDDYSTONE_FIELD_NUMBER: _ClassVar[int]
    ibeacon: Ibeacon
    eddystone: Eddystone
    def __init__(self, ibeacon: _Optional[_Union[Ibeacon, _Mapping]] = ..., eddystone: _Optional[_Union[Eddystone, _Mapping]] = ...) -> None: ...

class Accelerometer(_message.Message):
    __slots__ = ("x", "y", "z", "status")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    status: AccelStatus
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., status: _Optional[_Union[AccelStatus, str]] = ...) -> None: ...

class RockerSwitch(_message.Message):
    __slots__ = ("id", "state")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    id: str
    state: rockerSwitchPosition
    def __init__(self, id: _Optional[str] = ..., state: _Optional[_Union[rockerSwitchPosition, str]] = ...) -> None: ...

class Contact(_message.Message):
    __slots__ = ("id", "state")
    ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    id: int
    state: ContactPosition
    def __init__(self, id: _Optional[int] = ..., state: _Optional[_Union[ContactPosition, str]] = ...) -> None: ...

class Occupancy(_message.Message):
    __slots__ = ("level",)
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    level: int
    def __init__(self, level: _Optional[int] = ...) -> None: ...

class Sensors(_message.Message):
    __slots__ = ("accelerometer", "battery", "temperatureC", "humidity", "voltage", "illumination", "motion", "current", "CO", "CO2", "VOC", "resistance", "pressure", "alarm", "contact", "occupancy", "mechanicalHandle", "distance", "capacitance")
    ACCELEROMETER_FIELD_NUMBER: _ClassVar[int]
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    TEMPERATUREC_FIELD_NUMBER: _ClassVar[int]
    HUMIDITY_FIELD_NUMBER: _ClassVar[int]
    VOLTAGE_FIELD_NUMBER: _ClassVar[int]
    ILLUMINATION_FIELD_NUMBER: _ClassVar[int]
    MOTION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FIELD_NUMBER: _ClassVar[int]
    CO_FIELD_NUMBER: _ClassVar[int]
    CO2_FIELD_NUMBER: _ClassVar[int]
    VOC_FIELD_NUMBER: _ClassVar[int]
    RESISTANCE_FIELD_NUMBER: _ClassVar[int]
    PRESSURE_FIELD_NUMBER: _ClassVar[int]
    ALARM_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    OCCUPANCY_FIELD_NUMBER: _ClassVar[int]
    MECHANICALHANDLE_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    CAPACITANCE_FIELD_NUMBER: _ClassVar[int]
    accelerometer: Accelerometer
    battery: int
    temperatureC: float
    humidity: int
    voltage: float
    illumination: int
    motion: bool
    current: int
    CO: int
    CO2: int
    VOC: int
    resistance: float
    pressure: int
    alarm: _containers.RepeatedScalarFieldContainer[Alarm]
    contact: _containers.RepeatedCompositeFieldContainer[Contact]
    occupancy: Occupancy
    mechanicalHandle: MechanicalH
    distance: int
    capacitance: float
    def __init__(self, accelerometer: _Optional[_Union[Accelerometer, _Mapping]] = ..., battery: _Optional[int] = ..., temperatureC: _Optional[float] = ..., humidity: _Optional[int] = ..., voltage: _Optional[float] = ..., illumination: _Optional[int] = ..., motion: bool = ..., current: _Optional[int] = ..., CO: _Optional[int] = ..., CO2: _Optional[int] = ..., VOC: _Optional[int] = ..., resistance: _Optional[float] = ..., pressure: _Optional[int] = ..., alarm: _Optional[_Iterable[_Union[Alarm, str]]] = ..., contact: _Optional[_Iterable[_Union[Contact, _Mapping]]] = ..., occupancy: _Optional[_Union[Occupancy, _Mapping]] = ..., mechanicalHandle: _Optional[_Union[MechanicalH, str]] = ..., distance: _Optional[int] = ..., capacitance: _Optional[float] = ...) -> None: ...

class Stats(_message.Message):
    __slots__ = ("uptime", "adv_cnt", "seq_nr", "frame_cnt")
    UPTIME_FIELD_NUMBER: _ClassVar[int]
    ADV_CNT_FIELD_NUMBER: _ClassVar[int]
    SEQ_NR_FIELD_NUMBER: _ClassVar[int]
    FRAME_CNT_FIELD_NUMBER: _ClassVar[int]
    uptime: int
    adv_cnt: int
    seq_nr: int
    frame_cnt: int
    def __init__(self, uptime: _Optional[int] = ..., adv_cnt: _Optional[int] = ..., seq_nr: _Optional[int] = ..., frame_cnt: _Optional[int] = ...) -> None: ...

class Inputs(_message.Message):
    __slots__ = ("rocker", "switchIndex")
    ROCKER_FIELD_NUMBER: _ClassVar[int]
    SWITCHINDEX_FIELD_NUMBER: _ClassVar[int]
    rocker: _containers.RepeatedCompositeFieldContainer[RockerSwitch]
    switchIndex: _containers.RepeatedScalarFieldContainer[switchState]
    def __init__(self, rocker: _Optional[_Iterable[_Union[RockerSwitch, _Mapping]]] = ..., switchIndex: _Optional[_Iterable[_Union[switchState, str]]] = ...) -> None: ...

class VendorData(_message.Message):
    __slots__ = ("vendor", "data")
    VENDOR_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    vendor: str
    data: bytes
    def __init__(self, vendor: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class BTCompanyID(_message.Message):
    __slots__ = ("value", "description")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    value: int
    description: str
    def __init__(self, value: _Optional[int] = ..., description: _Optional[str] = ...) -> None: ...

class Reported(_message.Message):
    __slots__ = ("mac", "deviceClass", "model", "firmware", "assetId", "publicKey", "lastSeen", "bevent", "rssi", "cell", "beacons", "txpower", "sensors", "stats", "inputs", "vendorData", "vendorName", "sensorTimestamp", "flags", "localName", "identity", "companyIdentifier")
    MAC_FIELD_NUMBER: _ClassVar[int]
    DEVICECLASS_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_FIELD_NUMBER: _ClassVar[int]
    ASSETID_FIELD_NUMBER: _ClassVar[int]
    PUBLICKEY_FIELD_NUMBER: _ClassVar[int]
    LASTSEEN_FIELD_NUMBER: _ClassVar[int]
    BEVENT_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    CELL_FIELD_NUMBER: _ClassVar[int]
    BEACONS_FIELD_NUMBER: _ClassVar[int]
    TXPOWER_FIELD_NUMBER: _ClassVar[int]
    SENSORS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    VENDORDATA_FIELD_NUMBER: _ClassVar[int]
    VENDORNAME_FIELD_NUMBER: _ClassVar[int]
    SENSORTIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    FLAGS_FIELD_NUMBER: _ClassVar[int]
    LOCALNAME_FIELD_NUMBER: _ClassVar[int]
    IDENTITY_FIELD_NUMBER: _ClassVar[int]
    COMPANYIDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    mac: bytes
    deviceClass: _containers.RepeatedScalarFieldContainer[_aruba_iot_types_pb2.deviceClassEnum]
    model: str
    firmware: Firmware
    assetId: str
    publicKey: bytes
    lastSeen: int
    bevent: BeaconEvent
    rssi: Rssi
    cell: Cell
    beacons: _containers.RepeatedCompositeFieldContainer[Beacons]
    txpower: int
    sensors: Sensors
    stats: Stats
    inputs: Inputs
    vendorData: VendorData
    vendorName: str
    sensorTimestamp: int
    flags: int
    localName: str
    identity: str
    companyIdentifier: _containers.RepeatedCompositeFieldContainer[BTCompanyID]
    def __init__(self, mac: _Optional[bytes] = ..., deviceClass: _Optional[_Iterable[_Union[_aruba_iot_types_pb2.deviceClassEnum, str]]] = ..., model: _Optional[str] = ..., firmware: _Optional[_Union[Firmware, _Mapping]] = ..., assetId: _Optional[str] = ..., publicKey: _Optional[bytes] = ..., lastSeen: _Optional[int] = ..., bevent: _Optional[_Union[BeaconEvent, _Mapping]] = ..., rssi: _Optional[_Union[Rssi, _Mapping]] = ..., cell: _Optional[_Union[Cell, _Mapping]] = ..., beacons: _Optional[_Iterable[_Union[Beacons, _Mapping]]] = ..., txpower: _Optional[int] = ..., sensors: _Optional[_Union[Sensors, _Mapping]] = ..., stats: _Optional[_Union[Stats, _Mapping]] = ..., inputs: _Optional[_Union[Inputs, _Mapping]] = ..., vendorData: _Optional[_Union[VendorData, _Mapping]] = ..., vendorName: _Optional[str] = ..., sensorTimestamp: _Optional[int] = ..., flags: _Optional[int] = ..., localName: _Optional[str] = ..., identity: _Optional[str] = ..., companyIdentifier: _Optional[_Iterable[_Union[BTCompanyID, _Mapping]]] = ...) -> None: ...
