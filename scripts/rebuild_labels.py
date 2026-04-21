#!/usr/bin/env python3
"""Rebuild labels.csv: dedupe, keep last label, clean."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "datasets" / "labeled" / "labels.csv"
seen = {}  # text -> label
with path.open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        if len(row) >= 2:
            text = ",".join(row[:-1])
            label = row[-1].strip()
            if label in ("0", "1"):
                seen[text] = label

print(f"Loaded {len(seen)} unique rows")

# Append two JUNK corrections if missing
corrections = [
    ("spwwwwsssss0UUUUUUUUU77770wwwws77770UUUUUUUUU7ssspw", "1"),
    ("|$ POSIt", "1"),
]
added = 0
for text, label in corrections:
    if text not in seen:
        seen[text] = label
        added += 1
print(f"Added {added} corrections")

# Write back
with path.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["line", "label"])
    for text, label in seen.items():
        w.writerow([text, label])

# Report
k = sum(1 for v in seen.values() if v == "0")
j = sum(1 for v in seen.values() if v == "1")
n = k + j
print(f"Wrote {n} rows: KEEP={k} JUNK={j}")
print(f"Header: line,label")
