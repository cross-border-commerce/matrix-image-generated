"""测试用图片：生成纯色 PNG，避免依赖 Pillow。"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

# 1x1 透明 PNG，给接口校验、假生图用，体积小
MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def write_png(path: Path) -> Path:
    """写入最小 PNG，仅用于格式校验。"""
    path.write_bytes(MINIMAL_PNG)
    return path


def write_color_png(
    path: Path,
    width: int,
    height: int,
    rgb: tuple[int, int, int],
) -> Path:
    """写入指定尺寸的纯色 PNG，给真实生图接口当参考图。"""

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + (bytes(rgb) * width) for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    return path
