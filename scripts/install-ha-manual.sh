#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  cat >&2 <<'EOF'
Usage:
  scripts/install-ha-manual.sh /path/to/homeassistant/config

This copies:
  custom_components/aruba_ble_proxy -> <config>/custom_components/aruba_ble_proxy
EOF
  exit 2
fi

ha_config_dir="$1"

if [ ! -d "$ha_config_dir" ]; then
  echo "Home Assistant config directory not found: $ha_config_dir" >&2
  exit 1
fi

mkdir -p "$ha_config_dir/custom_components"
rm -rf "$ha_config_dir/custom_components/aruba_ble_proxy"
rm -rf "$ha_config_dir/aruba_ble_proxy"
cp -R custom_components/aruba_ble_proxy "$ha_config_dir/custom_components/"

echo "Installed Aruba BLE Proxy custom integration into $ha_config_dir"
echo "Restart Home Assistant, then add the Aruba BLE Proxy integration."
