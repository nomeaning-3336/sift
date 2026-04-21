"""Pure-Python printable string extraction used as a cross-platform fallback."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


PRINTABLE_ASCII = set(range(0x20, 0x7F)) | {0x09}


def is_printable_ascii_byte(value: int) -> bool:
    return value in PRINTABLE_ASCII


def extract_ascii_strings(data: bytes, min_len: int = 4) -> Iterable[str]:
    start = None
    buf = bytearray()
    for index, byte in enumerate(data):
        if is_printable_ascii_byte(byte):
            if start is None:
                start = index
            buf.append(byte)
        else:
            if start is not None and len(buf) >= min_len:
                yield buf.decode("ascii", errors="ignore")
            start = None
            buf.clear()
    if start is not None and len(buf) >= min_len:
        yield buf.decode("ascii", errors="ignore")


def extract_utf16le_strings(data: bytes, min_len: int = 4) -> Iterable[str]:
    start = None
    chars: list[str] = []
    index = 0
    size = len(data)
    while index + 1 < size:
        lo = data[index]
        hi = data[index + 1]
        if hi == 0x00 and is_printable_ascii_byte(lo):
            if start is None:
                start = index
            chars.append(chr(lo))
            index += 2
        else:
            if start is not None and len(chars) >= min_len:
                yield "".join(chars)
            start = None
            chars.clear()
            index += 1
    if start is not None and len(chars) >= min_len:
        yield "".join(chars)


def extract_strings_from_path(path: Path, min_len: int = 4) -> list[str]:
    data = path.read_bytes()
    results = list(extract_ascii_strings(data, min_len=min_len))
    results.extend(extract_utf16le_strings(data, min_len=min_len))
    return results
