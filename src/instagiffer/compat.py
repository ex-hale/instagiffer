"""Compatibility things for Python versions."""

import sys
import uuid

if sys.version_info < (3, 14):  # noqa: UP036
    import os
    import time

    def uuid7() -> uuid.UUID:
        timestamp_ms = int(time.time() * 1000)
        ts_bits = timestamp_ms & 0xFFFFFFFFFFFF
        rand_a = int.from_bytes(os.urandom(2)) & 0x0FFF
        rand_b = int.from_bytes(os.urandom(8)) & 0x3FFFFFFFFFFFFFFF
        int_val = (ts_bits << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
        return uuid.UUID(int=int_val)
else:
    uuid7 = uuid.uuid7
