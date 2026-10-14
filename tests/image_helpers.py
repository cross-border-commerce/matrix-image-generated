"""测试用最小 PNG，给接口校验和假生图用。"""

from pathlib import Path

MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def write_png(path: Path) -> Path:
    """写入最小 PNG，仅用于格式校验。"""
    path.write_bytes(MINIMAL_PNG)
    return path

