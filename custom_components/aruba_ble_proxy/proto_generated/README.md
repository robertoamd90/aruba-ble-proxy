# Generated Aruba Protobuf Modules

This directory is the default output target for `scripts/generate-aruba-protobuf.sh`.

The generated `aruba_iot_*_pb2.py` files are produced from Aruba's official
`proto_files/source` directory.

They are committed to this repository on purpose so a fresh clone can run and
test the Home Assistant integration without also cloning Aruba's reference
repository. The optional local
[`vendor/aos8-iot-server-example-websocket`](https://github.com/aruba/aos8-iot-server-example-websocket)
directory is only needed when regenerating these files.
