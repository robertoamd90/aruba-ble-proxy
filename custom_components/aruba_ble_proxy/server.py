from __future__ import annotations

import sys

from .aruba_iot_ble import server as _impl

sys.modules[__name__] = _impl
