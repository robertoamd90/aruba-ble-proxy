# Roadmap 1.0 - Aruba BLE Proxy

This file records the 1.0 release decisions. It is intentionally short: items
that are not required for 1.0 stay out of the release scope.

## 1.0 Scope

- Passive BLE advertisement forwarding through Aruba APs.
- Aruba APs registered as Home Assistant Bluetooth scanner sources.
- Active BLE/GATT connector enabled by default.
- Configurable active BLE connection slots per AP.
- Source-scoped active state for multi-AP deployments.
- Manual Aruba BLE/GATT services for diagnostics and direct actions.
- Narrow SwitchBot command-service fallback for devices advertising `FD3D` when
  Aruba does not report the known command characteristics.

## Explicit Non-Scope

- BLE pairing, bonding, unpairing, and descriptor read/write.
- Device payload parsing or repair.
- BTHome/Xiaomi/Shelly/SwitchBot application protocol decoding.
- Generic invention of GATT characteristics when Aruba discovery is incomplete.
- Advertisement deduplication or AP best-source selection in the proxy.
- New vendor-specific compatibility fallbacks.

## 1.0 Release Changes

- Manifest version set to `1.0.0`.
- README, SPEC, install notes, field-test docs, and translations updated so
  active BLE/GATT is no longer described as experimental.
- Active BLE connection slot default set to 3 per AP.
- SwitchBot fallback left functionally unchanged and documented as a narrow
  compatibility fallback, not a generic discovery replacement.
- WebSocket sends to Aruba APs now have a bounded timeout so a blocked socket
  cannot hold the per-AP send lock indefinitely.
- Receiver task crashes are surfaced in diagnostics.
- Long-lived advertisement diagnostic sets and advertised-service caches are
  bounded.

## Post-1.0 Candidates

- Add more concurrency tests around disconnect versus in-flight GATT operations.
- Split `runtime.py` only if future changes require deeper refactoring.
