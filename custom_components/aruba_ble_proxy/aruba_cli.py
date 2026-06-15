from __future__ import annotations

import sys

from .aruba_iot_ble import aruba_cli as _impl

sys.modules[__name__] = _impl
