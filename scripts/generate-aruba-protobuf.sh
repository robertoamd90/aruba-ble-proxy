#!/usr/bin/env bash
set -euo pipefail

proto_dir="${ARUBA_PROTO_DIR:-vendor/aos8-iot-server-example-websocket/proto_files/source}"
out_dir="${ARUBA_PROTO_OUT:-custom_components/aruba_ble_proxy/proto_generated}"

if [ ! -d "$proto_dir" ]; then
  cat >&2 <<EOF
Aruba proto directory not found: $proto_dir

Set ARUBA_PROTO_DIR to a local copy of Aruba's proto_files/source directory, or place:
  https://github.com/aruba/aos8-iot-server-example-websocket
under:
  vendor/aos8-iot-server-example-websocket
EOF
  exit 1
fi

mkdir -p "$out_dir"

if command -v protoc >/dev/null 2>&1; then
  protoc_cmd=(protoc)
else
  python_bin="${PYTHON:-python3}"
  protoc_cmd=("$python_bin" -m grpc_tools.protoc)
fi

"${protoc_cmd[@]}" \
  -I="$proto_dir" \
  --python_out="$out_dir" \
  --pyi_out="$out_dir" \
  "$proto_dir"/aruba-iot-*

echo "Generated Aruba protobuf modules in $out_dir"
