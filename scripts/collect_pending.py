#!/usr/bin/env python3
"""
collect_pending.py - collect unlabeled predictions for human review

Loop:
1. Find ELF/PE executables
2. Run: python tools/pystrings.py file | sift --show-labels
3. Parse [KEEP/JUNK prob%] text
4. Append to datasets/labeled/pending_labels.csv

Stop when pending_labels.csv has 10,000 entries.
"""
import csv
import os
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYSTRINGS = ROOT / "tools" / "pystrings.py"
PENDING = ROOT / "datasets" / "labeled" / "pending_labels.csv"
TARGET = 10000

PAT = re.compile(r"^\[(KEEP|JUNK)\s+\d+%\]\s?(.*)$")


def find_binaries():
    """Find executables in common locations (Windows-aware paths)."""
    dirs = [
        "C:/Program Files/Git/bin",
        "C:/Program Files/Git/usr/bin",
        "C:/Windows/System32",
        "C:/Program Files",
        "C:/Program Files (x86)",
    ]
    seen = set()
    bins = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            for entry in os.listdir(d):
                path = os.path.join(d, entry)
                if path in seen:
                    continue
                seen.add(path)
                if not os.path.isfile(path):
                    continue
                low = entry.lower()
                # Only .exe files (skip DLLs, scripts, etc.)
                if not low.endswith(".exe"):
                    continue
                if "~" in entry:
                    continue
                bins.append(path)
        except OSError:
            pass
    random.shuffle(bins)
    return bins


def collect_from_binary(path):
    """Run pystrings + sift on a binary, return list of (text, label_str)."""
    try:
        # pystrings
        p = subprocess.run(
            [sys.executable, str(PYSTRINGS), path],
            capture_output=True, text=True, errors="replace", timeout=30
        )
        strings_output = p.stdout
    except Exception as e:
        print(f"  pystrings failed: {e}", file=sys.stderr)
        return []

    lines = strings_output.splitlines()
    # Sample up to 1000, shuffle
    random.shuffle(lines)
    if len(lines) > 1000:
        lines = lines[:1000]

    if not lines:
        return []

    # Pipe to sift
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        p = subprocess.run(
            [sys.executable, "-m", "sift", "--show-labels"],
            input="\n".join(lines),
            capture_output=True, text=True, errors="replace", timeout=30, env=env
        )
        output = p.stdout
    except Exception as e:
        print(f"  sift failed: {e}", file=sys.stderr)
        return []

    results = []
    for line in output.splitlines():
        m = PAT.match(line)
        if not m:
            continue
        tag = m.group(1)
        text = m.group(2)
        results.append((text, tag))

    return results


def append_pending(rows):
    """Append (text, label_str) rows to pending CSV."""
    os.makedirs(os.path.dirname(PENDING), exist_ok=True)
    mode = "a" if PENDING.exists() else "w"
    with open(PENDING, mode, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["line", "label"])
        for text, label in rows:
            w.writerow([text, label])


def main():
    if PENDING.exists():
        with open(PENDING, "r", encoding="utf-8") as f:
            existing = sum(1 for _ in f) - 1  # minus header
        print(f"pending_labels.csv already has {existing} rows")
    else:
        existing = 0

    need = TARGET - existing
    if need <= 0:
        print(f"Already have {existing} >= {TARGET}, nothing to do")
        return

    print(f"Need {need} more pending labels. Finding binaries...")
    binaries = find_binaries()
    print(f"Found {len(binaries)} binaries")

    collected = 0
    for i, binpath in enumerate(binaries):
        if collected >= need:
            break
        print(f"[{i+1}/{len(binaries)}] {binpath}...", end=" ", flush=True)
        rows = collect_from_binary(binpath)
        if not rows:
            print("0 rows")
            continue
        append_pending(rows)
        collected += len(rows)
        print(f"+{len(rows)} rows (total pending: {existing + collected})")

    final = existing + collected
    print(f"\nDone. pending_labels.csv now has ~{final} rows (target: {TARGET})")
    if final < TARGET:
        print(f"WARNING: only collected {final}, need {TARGET - final} more. Run again.")


if __name__ == "__main__":
    main()
