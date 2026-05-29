import aruba_iot_types_pb2 as _aruba_iot_types_pb2
import aruba_iot_nb_telemetry_pb2 as _aruba_iot_nb_telemetry_pb2
import aruba_iot_nb_action_results_pb2 as _aruba_iot_nb_action_results_pb2
import aruba_iot_nb_characteristic_pb2 as _aruba_iot_nb_characteristic_pb2
import aruba_iot_nb_ble_data_pb2 as _aruba_iot_nb_ble_data_pb2
import aruba_iot_nb_wifi_data_pb2 as _aruba_iot_nb_wifi_data_pb2
import aruba_iot_nb_device_count_pb2 as _aruba_iot_nb_device_count_pb2
import aruba_iot_nb_status_pb2 as _aruba_iot_nb_status_pb2
import aruba_iot_nb_zb_pb2 as _aruba_iot_nb_zb_pb2
import aruba_iot_nb_serial_data_pb2 as _aruba_iot_nb_serial_data_pb2
import aruba_iot_nb_ap_health_update_pb2 as _aruba_iot_nb_ap_health_update_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Reporter(_message.Message):
    __slots__ = ("name", "mac", "ipv4", "ipv6", "hwType", "swVersion", "swBuild", "time")
    NAME_FIELD_NUMBER: _ClassVar[int]
    MAC_FIELD_NUMBER: _ClassVar[int]
    IPV4_FIELD_NUMBER: _ClassVar[int]
    IPV6_FIELD_NUMBER: _ClassVar[int]
    HWTYPE_FIELD_NUMBER: _ClassVar[int]
    SWVERSION_FIELD_NUMBER: _ClassVar[int]
    SWBUILD_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    name: str
    mac: bytes
    ipv4: str
    ipv6: str
    hwType: str
    swVersion: str
    swBuild: str
    time: int
    def __init__(self, name: _Optional[str] = ..., mac: _Optional[bytes] = ..., ipv4: _Optional[str] = ..., ipv6: _Optional[str] = ..., hwType: _Optional[str] = ..., swVersion: _Optional[str] = ..., swBuild: _Optional[str] = ..., time: _Optional[int] = ...) -> None: ...

class Telemetry(_message.Message):
    __slots__ = ("meta", "reporter", "reported", "results", "characteristics", "bleData", "wifiData", "devCount", "status", "zigbee", "nbSData", "apHealth")
    META_FIELD_NUMBER: _ClassVar[int]
    REPORTER_FIELD_NUMBER: _ClassVar[int]
    REPORTED_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    CHARACTERISTICS_FIELD_NUMBER: _ClassVar[int]
    BLEDATA_FIELD_NUMBER: _ClassVar[int]
    WIFIDATA_FIELD_NUMBER: _ClassVar[int]
    DEVCOUNT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ZIGBEE_FIELD_NUMBER: _ClassVar[int]
    NBSDATA_FIELD_NUMBER: _ClassVar[int]
    APHEALTH_FIELD_NUMBER: _ClassVar[int]
    meta: _aruba_iot_types_pb2.Meta
    reporter: Reporter
    reported: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_telemetry_pb2.Reported]
    results: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_action_results_pb2.ActionResult]
    characteristics: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_characteristic_pb2.Characteristic]
    bleData: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_ble_data_pb2.BleData]
    wifiData: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_wifi_data_pb2.WiFiData]
    devCount: _aruba_iot_nb_device_count_pb2.DeviceCount
    status: _aruba_iot_nb_status_pb2.Status
    zigbee: _aruba_iot_nb_zb_pb2.NbZbMsg
    nbSData: _containers.RepeatedCompositeFieldContainer[_aruba_iot_nb_serial_data_pb2.NbSerialData]
    apHealth: _aruba_iot_nb_ap_health_update_pb2.ApHealthUpdate
    def __init__(self, meta: _Optional[_Union[_aruba_iot_types_pb2.Meta, _Mapping]] = ..., reporter: _Optional[_Union[Reporter, _Mapping]] = ..., reported: _Optional[_Iterable[_Union[_aruba_iot_nb_telemetry_pb2.Reported, _Mapping]]] = ..., results: _Optional[_Iterable[_Union[_aruba_iot_nb_action_results_pb2.ActionResult, _Mapping]]] = ..., characteristics: _Optional[_Iterable[_Union[_aruba_iot_nb_characteristic_pb2.Characteristic, _Mapping]]] = ..., bleData: _Optional[_Iterable[_Union[_aruba_iot_nb_ble_data_pb2.BleData, _Mapping]]] = ..., wifiData: _Optional[_Iterable[_Union[_aruba_iot_nb_wifi_data_pb2.WiFiData, _Mapping]]] = ..., devCount: _Optional[_Union[_aruba_iot_nb_device_count_pb2.DeviceCount, _Mapping]] = ..., status: _Optional[_Union[_aruba_iot_nb_status_pb2.Status, _Mapping]] = ..., zigbee: _Optional[_Union[_aruba_iot_nb_zb_pb2.NbZbMsg, _Mapping]] = ..., nbSData: _Optional[_Iterable[_Union[_aruba_iot_nb_serial_data_pb2.NbSerialData, _Mapping]]] = ..., apHealth: _Optional[_Union[_aruba_iot_nb_ap_health_update_pb2.ApHealthUpdate, _Mapping]] = ...) -> None: ...
