#!/usr/bin/env python3
"""
pystrings.py - extract printable strings from binary files

Usage:
    python tools/pystrings.py file.exe
    python tools/pystrings.py file1.bin file2.dll
    type file.exe | python tools/pystrings.py -
    python tools/pystrings.py -n 4 --encoding ascii file.bin
    python tools/pystrings.py --offsets file.bin

Notes:
- '-' means read from stdin (binary).
- Default minimum string length is 4.
- Supports ASCII and UTF-16LE extraction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import BinaryIO, Iterable


PRINTABLE_ASCII = set(range(0x20, 0x7F)) | {0x09}  # tab allowed


def is_printable_ascii_byte(b: int) -> bool:
    return b in PRINTABLE_ASCII


def extract_ascii_strings(
    data: bytes,
    min_len: int,
) -> Iterable[tuple[int, str]]:
    start = None
    buf = bytearray()

    for i, b in enumerate(data):
        if is_printable_ascii_byte(b):
            if start is None:
                start = i
            buf.append(b)
        else:
            if start is not None and len(buf) >= min_len:
                yield start, buf.decode("ascii", errors="ignore")
            start = None
            buf.clear()

    if start is not None and len(buf) >= min_len:
        yield start, buf.decode("ascii", errors="ignore")


def extract_utf16le_strings(
    data: bytes,
    min_len: int,
) -> Iterable[tuple[int, str]]:
    start = None
    chars: list[str] = []

    i = 0
    n = len(data)
    while i + 1 < n:
        lo = data[i]
        hi = data[i + 1]

        if hi == 0x00 and is_printable_ascii_byte(lo):
            if start is None:
                start = i
            chars.append(chr(lo))
            i += 2
        else:
            if start is not None and len(chars) >= min_len:
                yield start, "".join(chars)
            start = None
            chars.clear()
            i += 1

    if start is not None and len(chars) >= min_len:
        yield start, "".join(chars)


def read_all(fp: BinaryIO) -> bytes:
    return fp.read()


def process_stream(
    name: str,
    fp: BinaryIO,
    min_len: int,
    encodings: list[str],
    show_offsets: bool,
    show_filename: bool,
) -> None:
    data = read_all(fp)

    results: list[tuple[int, str]] = []

    if "ascii" in encodings:
        results.extend(extract_ascii_strings(data, min_len))

    if "utf16le" in encodings:
        results.extend(extract_utf16le_strings(data, min_len))

    results.sort(key=lambda x: x[0])

    for offset, text in results:
        parts = []
        if show_filename:
            parts.append(f"{name}:")
        if show_offsets:
            parts.append(f"{offset:08x}")
        parts.append(text)
        print(" ".join(parts))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract printable strings from binary files.")
    p.add_argument(
        "files",
        nargs="+",
        help="Files to scan, or '-' for stdin",
    )
    p.add_argument(
        "-n",
        "--min-length",
        type=int,
        default=4,
        help="Minimum string length (default: 4)",
    )
    p.add_argument(
        "-e",
        "--encoding",
        choices=["ascii", "utf16le", "both"],
        default="ascii",
        help="String encoding to extract (default: ascii)",
    )
    p.add_argument(
        "-o",
        "--offsets",
        action="store_true",
        help="Show file offsets",
    )
    p.add_argument(
        "-f",
        "--filenames",
        action="store_true",
        help="Always show filenames",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    encodings = ["ascii", "utf16le"] if args.encoding == "both" else [args.encoding]
    show_filename = args.filenames or len(args.files) > 1

    for file_arg in args.files:
        if file_arg == "-":
            process_stream(
                name="<stdin>",
                fp=sys.stdin.buffer,
                min_len=args.min_length,
                encodings=encodings,
                show_offsets=args.offsets,
                show_filename=show_filename,
            )
            continue

        path = Path(file_arg)
        try:
            with path.open("rb") as f:
                process_stream(
                    name=str(path),
                    fp=f,
                    min_len=args.min_length,
                    encodings=encodings,
                    show_offsets=args.offsets,
                    show_filename=show_filename,
                )
        except OSError as e:
            print(f"pystrings: {path}: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
