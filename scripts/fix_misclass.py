#!/usr/bin/env python3
"""Append only new misclassified holdout rows to labels.csv."""

import argparse
import csv
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_csv_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            label_text = row[-1].strip()
            if label_text not in ("0", "1"):
                continue
            rows.append((",".join(row[:-1]), int(label_text)))
    return rows


def load_known_labels(path):
    if not path.exists():
        return set()
    return set(load_csv_rows(path))


def main():
    parser = argparse.ArgumentParser(description="Append new misclassified holdout rows to labels.csv")
    parser.add_argument("--holdout", default="datasets/labeled/holdout_adversarial.csv")
    parser.add_argument("--labels", default="datasets/labeled/labels.csv")
    parser.add_argument("--model", default="src/sift/models/sift.pkl")
    args = parser.parse_args()

    model_path = ROOT / args.model
    holdout_path = ROOT / args.holdout
    labels_path = ROOT / args.labels

    with open(model_path, "rb") as handle:
        flt = pickle.load(handle)

    existing = load_known_labels(labels_path)
    misclassified = []

    for text, true_label in load_csv_rows(holdout_path):
        prob = flt.predict_proba([text])[0][1]
        pred = 1 if prob >= 0.5 else 0
        if pred != true_label and (text, true_label) not in existing:
            misclassified.append((text, true_label, prob))

    print(f"Misclassified on {holdout_path}: {len(misclassified)}")
    for text, true_label, prob in misclassified:
        label_name = "JUNK" if true_label == 1 else "KEEP"
        print(f"  [{label_name} @ {prob:.0%}] {text[:80]}")

    if not misclassified:
        print("No new mistakes to append.")
        return

    labels_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not labels_path.exists()
    with open(labels_path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(["line", "label"])
        for text, true_label, _ in misclassified:
            writer.writerow([text, true_label])

    print(f"Appended {len(misclassified)} new mistakes to {labels_path}")


if __name__ == "__main__":
    main()
