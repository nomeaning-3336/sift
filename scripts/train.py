#!/usr/bin/env python3
"""Sift Training Script - Human-in-the-Loop Labeling

Run this to improve the model by labeling uncertain lines.
Continues until unambiguous rate is below 1%%.
"""

import argparse
import csv
import hashlib
import os
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sift.model import JunkFilter, is_likely_junk


UNCERTAIN_MARGIN = 0.15


def load_labels(path):
    if not os.path.exists(path):
        return []
    labels = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 2:
                try:
                    label = int(row[-1])
                    text = ",".join(row[:-1])
                    labels.append((text, label))
                except (ValueError, IndexError):
                    pass
    return labels


def save_labels(labeled, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "a" if os.path.exists(path) else "w"
    with open(path, mode, encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if mode == "w":
            writer.writerow(["line", "label"])
        for line, label in labeled:
            writer.writerow([line, label])


def retrain(flt, labels_path, model_path):
    existing = load_labels(labels_path)
    if existing:
        texts, y = zip(*existing)
        if flt._is_fitted:
            flt.partial_fit(list(texts), list(y))
        else:
            flt.fit(list(texts), list(y))
        with open(model_path, "wb") as f:
            pickle.dump(flt, f)
    return flt


def get_uncertain_lines(lines, flt, threshold):
    uncertain = []
    for line in lines:
        line = line.rstrip("\n\r")
        if is_likely_junk(line):
            continue
        prob_junk = flt.predict_proba([line])[0][1]
        if abs(prob_junk - threshold) < UNCERTAIN_MARGIN or (0.3 < prob_junk < 0.7):
            uncertain.append(line)
    return uncertain


def interactive_label(uncertain_lines, flt, labels_path, model_path):
    print("\n" + "=" * 60)
    print("INTERACTIVE LABELING")
    print("=" * 60)
    print("[j] junk  [k] keep  [s] skip  [q] quit")
    print("-" * 60)
    new_labels = []
    for i, line in enumerate(uncertain_lines[:50], 1):
        prob_junk = flt.predict_proba([line])[0][1]
        print(f"\n[{i}] {repr(line[:80])}")
        print(f"    p_junk={prob_junk:.2%}")
        try:
            resp = sys.stdin.readline().strip().lower()
        except:
            break
        if resp == "q":
            break
        elif resp in ("j", "k"):
            new_labels.append((line, 1 if resp == "j" else 0))
    if new_labels:
        save_labels(new_labels, labels_path)
        flt = retrain(flt, labels_path, model_path)
        print(f"Updated with {len(new_labels)} labels.")
    return flt, new_labels


def main():
    p = argparse.ArgumentParser(description="Sift Training - Label Uncertain Lines")
    p.add_argument("--input", "-i", help="Input file to label (optional)")
    p.add_argument("--threshold", type=float, default=0.95)
    p.add_argument("--target-rate", type=float, default=0.01,
                   help="Target unambiguous rate (default: 0.01 = 1%%)")
    p.add_argument("--model", default="src/sift/models/sift.pkl")
    p.add_argument("--labels", default="datasets/labeled/labels.csv")
    args = p.parse_args()

    model_path = ROOT / args.model
    labels_path = ROOT / args.labels

    model_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.parent.mkdir(parents=True, exist_ok=True)

    # Load or create model
    flt = JunkFilter(threshold=args.threshold)
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                flt = pickle.load(f)
            flt.threshold = args.threshold
            print(f"Loaded model from {model_path}", file=sys.stderr)
        except:
            print("Could not load model, starting fresh", file=sys.stderr)
    else:
        print("No model found, starting fresh", file=sys.stderr)

    # Load existing labels
    existing = load_labels(str(labels_path))
    if existing:
        print(f"Loaded {len(existing)} existing labels", file=sys.stderr)
        texts, y = zip(*existing)
        if flt._is_fitted:
            flt.partial_fit(list(texts), list(y))
        else:
            flt.fit(list(texts), list(y))

    # Determine input lines
    if args.input:
        with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        print(f"Loaded {len(lines)} lines from {args.input}", file=sys.stderr)
    else:
        # Use stdin
        if sys.stdin.isatty():
            print("No input file specified and no stdin. Use --input or pipe data.", file=sys.stderr)
            return
        import io
        stdin_binary = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore")
        lines = stdin_binary.readlines()
        print(f"Loaded {len(lines)} lines from stdin", file=sys.stderr)

    # Dedupe
    seen = set()
    unique = []
    for l in lines:
        h = hashlib.md5(l.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(l)
    lines = unique

    # Labeling loop
    iteration = 0
    while True:
        iteration += 1
        uncertain = get_uncertain_lines(lines, flt, args.threshold)

        # Calculate unambiguous rate
        kept, junk = [], []
        for line in lines:
            line = line.rstrip("\n\r")
            if is_likely_junk(line):
                junk.append(line)
                continue
            prob_junk = flt.predict_proba([line])[0][1]
            if prob_junk >= args.threshold:
                junk.append(line)
            elif abs(prob_junk - args.threshold) < UNCERTAIN_MARGIN or (0.3 < prob_junk < 0.7):
                pass  # uncertain
            else:
                kept.append(line)

        total_classified = len(kept) + len(junk)
        if total_classified > 0:
            unambig_rate = len(uncertain) / (len(uncertain) + total_classified)
        else:
            unambig_rate = 1.0

        print(f"\n--- Iteration {iteration} ---", file=sys.stderr)
        print(f"Unambiguous rate: {unambig_rate:.1%} (target: {args.target_rate:.1%})", file=sys.stderr)
        print(f"Uncertain: {len(uncertain)}, Kept: {len(kept)}, Junk: {len(junk)}", file=sys.stderr)

        if unambig_rate <= args.target_rate:
            print(f"\nTarget reached! Unambiguous rate {unambig_rate:.1%} <= {args.target_rate:.1%}", file=sys.stderr)
            break

        if not uncertain:
            print("\nNo more uncertain lines to label.", file=sys.stderr)
            break

        # Interactive labeling
        flt, new = interactive_label(uncertain, flt, str(labels_path), str(model_path))
        if not new:
            print("No more labels added, stopping.", file=sys.stderr)
            break

    print(f"\nTraining complete. Model saved to {model_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
