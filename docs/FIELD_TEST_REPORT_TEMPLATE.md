# Field Test Report Template

Use this template for candidate `0.3.0b2`.

## Environment

```text
Candidate:
Bundle SHA256:
Home Assistant version:
Install method: manual custom_components copy / zip extract / other
Aruba AP model:
Aruba firmware:
Aruba AP MAC:
Aruba WebSocket URL configured:
Other Bluetooth radios disabled: yes/no
```

## Passive BLE

```text
Receiver connected sources:
Receiver last peer:
BLE advertisements counter increased: yes/no
Bluetooth advertisements page shows Aruba source: yes/no
BTHome updates through Aruba only: yes/no/not tested
SwitchBot thermometer updates through Aruba only: yes/no/not tested
Passive result: pass/fail
Notes:
```

## Home Assistant Bluetooth Source

```text
Aruba AP appears in Bluetooth graph: yes/no
BLE devices linked to Aruba AP source: yes/no
Integration disable stops Aruba-sourced updates: yes/no/not tested
Integration re-enable restores Aruba-sourced updates: yes/no/not tested
Startup blocked warning from Aruba receiver: yes/no
Scanner result: pass/fail
Notes:
```

## Manual Active GATT

```text
Test BLE device:
Device MAC:
Readable service UUID:
Readable characteristic UUID:

ble_connect status:
ble_connect full response:

gatt_read status:
gatt_read value:
gatt_read full response:

ble_disconnect status:
ble_disconnect full response:

Active BLE operations in flight after disconnect:
Active BLE operations waiting after disconnect:
Active BLE pending characteristic reads after disconnect:
Active BLE pending device discoveries after disconnect:
Active BLE notification subscriptions after disconnect:

Manual GATT result: pass/fail/not tested
Notes:
```

## SwitchBot Lock / Lock Pro

```text
Lock model:
Lock MAC:
SwitchBot integration setup result:
Discovery error, if any:
Command tested:
Command result:
Home Assistant error text:

Active BLE last action:
Active BLE last action duration:
Active BLE slowest action duration:
Active BLE last action error:
Active BLE action failures:
Active BLE action timeouts:
Active BLE last characteristic wait duration:
Active BLE slowest characteristic wait duration:
Active BLE notification updates:
Active BLE notification callback errors:

Counters stuck after failure: yes/no
Passive sensors still updated during test: yes/no
SwitchBot result: pass/fail/not tested
Notes:
```

## Logs

Paste relevant log lines only:

```text
custom_components.aruba_ble_proxy:

homeassistant.components.bluetooth:

bleak:

switchbot:
```

## Aruba CLI Evidence

```text
show iot transportProfile:

show running-config | include iot:

ping <Home Assistant host>:
```

## Decision

```text
Candidate usable for passive path: yes/no
Candidate usable for active GATT diagnostics: yes/no
Candidate usable for SwitchBot Lock workflow: yes/no
Promote active BLE toward 1.0 support: yes/no
Keep active BLE experimental/disabled by default: yes/no
Blocking bugs found:
```
