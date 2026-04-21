#!/usr/bin/env python3
"""
review_iteration.py - Iterative review of pending labels with human judgment

Loop:
1. Sample 200 pending rows
2. Show model prediction + probability per row
3. Human marks: correct / wrong / skip
4. Append corrections to labels.csv
5. Retrain model
6. Check against holdout set
7. Stop when holdout error rate is low and stable

Usage:
    python scripts/review_iteration.py
"""
import csv
import os
import pickle
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sift.model import JunkFilter

PENDING = ROOT / "datasets" / "labeled" / "pending_labels.csv"
LABELS = ROOT / "datasets" / "labeled" / "labels.csv"
HOLDOUT = ROOT / "datasets" / "labeled" / "holdout_adversarial.csv"
MODEL = ROOT / "src" / "sift" / "models" / "sift.pkl"
SAMPLE = 200


def load_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                rows.append(row)
    return rows


def load_labels(path):
    """Load labels, normalizing string KEEP/JUNK to int 0/1."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 2:
                label_str = row[-1].strip()
                if label_str == "KEEP":
                    label = 0
                elif label_str == "JUNK":
                    label = 1
                else:
                    try:
                        label = int(label_str)
                    except ValueError:
                        continue
                rows.append((",".join(row[:-1]), label))
    return rows


def save_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["line", "label"])
        for r in rows:
            w.writerow(r)


def append_to_labels(corrections):
    mode = "a" if LABELS.exists() else "w"
    with LABELS.open(mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["line", "label"])
        for text, label in corrections:
            w.writerow([text, label])


def retrain():
    rows = load_labels(LABELS)
    if not rows:
        return None, 0
    texts, y = zip(*rows)
    flt = JunkFilter(threshold=0.5)
    flt.fit(list(texts), list(y))
    with open(MODEL, "wb") as f:
        pickle.dump(flt, f)
    return flt, len(texts)


def holdout_stats(flt):
    tp = tn = fp = fn = 0
    for text, true_label in load_labels(HOLDOUT):
        prob = flt.predict_proba([text])[0][1]
        pred = 1 if prob >= 0.5 else 0
        if pred == 1 and true_label == 1:
            tp += 1
        elif pred == 0 and true_label == 0:
            tn += 1
        elif pred == 1 and true_label == 0:
            fp += 1
        else:
            fn += 1
    total = tp + tn + fp + fn
    acc = (tp + tn) / total if total else 0
    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0
    return {"acc": acc, "prec": prec, "rec": rec, "fp": fp, "fn": fn, "total": total}


def review_sample(flt, sample_rows):
    """Present rows to human. Returns list of (text, corrected_label) for wrong rows."""
    corrections = []
    confirmed = 0

    print(f"\nReview {len(sample_rows)} sampled predictions. ")
    print("Format: [MODEL@prob%] text ...\n")

    for i, (text, model_pred_str) in enumerate(sample_rows):
        prob = flt.predict_proba([text])[0][1]
        model_label = 1 if model_pred_str == "JUNK" else 0
        model_tag = "JUNK" if model_label == 1 else "KEEP"

        print(f"[{i+1}] [{model_tag} {prob:>5.0%}] {text[:75]}")

        resp = input("  → [k=keep correct, j=junk correct, w=wrong, s=skip]: ").strip().lower()

        if resp == "w":
            # Wrong: human will provide correct label
            print(f"     Current: {model_tag}. Correct label? ", end="")
            correct = input("[k=keep/0, j=junk/1]: ").strip().lower()
            if correct == "j":
                corrections.append((text, 1))
            elif correct == "k":
                corrections.append((text, 0))
            else:
                print("     Skipped.")
        elif resp == "k":
            confirmed += 1
        elif resp == "j":
            confirmed += 1

    return corrections, confirmed


def main():
    random.seed()
    iteration = 1
    prev_fp = prev_fn = None

    while True:
        pending = load_rows(PENDING)
        if not pending:
            print("No more pending rows. Done!")
            break

        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"Pending: {len(pending)}, Labels: {load_rows(LABELS).__len__()}, Holdout: {load_rows(HOLDOUT).__len__()}")
        print("=" * 60)

        # Retrain
        flt, n_labels = retrain()
        if flt is None:
            print("No labels yet. Train the model first.")
            break

        # Holdout eval
        stats = holdout_stats(flt)
        print(f"\nHoldout ({stats['total']} rows): "
              f"acc={stats['acc']:.1%} prec={stats['prec']:.1%} rec={stats['rec']:.1%}  "
              f"fp={stats['fp']} fn={stats['fn']}")

        # Stop check
        if iteration >= 3 and stats['fp'] <= 5 and stats['fn'] <= 5:
            print(f"\nStop criterion met: fp={stats['fp']} fn={stats['fn']} after {iteration} iters.")
            break

        if (prev_fp is not None and stats['fp'] >= prev_fp - 1
                and stats['fn'] >= prev_fn - 1 and iteration >= 3):
            print(f"\nNo improvement (fp: {prev_fp}→{stats['fp']}, fn: {prev_fn}→{stats['fn']}). Stopping.")
            break

        prev_fp = stats['fp']
        prev_fn = stats['fn']

        # Sample and review
        sample = random.sample(pending, min(SAMPLE, len(pending)))
        corrections, confirmed = review_sample(flt, sample)

        if corrections:
            append_to_labels(corrections)
            # Remove corrected rows from pending
            correction_set = {(c[0],) for c in corrections}
            new_pending = [r for r in pending if tuple(r) not in correction_set]
            save_csv(new_pending, PENDING)
            print(f"\nAppended {len(corrections)} corrections. {len(new_pending)} pending remain.")
        else:
            print("\nNo corrections this iteration.")

        print(f"Confirmed: {confirmed}/{len(sample)}")

        iteration += 1

    print(f"\nFinal: {load_rows(LABELS).__len__()} labels, {load_rows(PENDING).__len__()} pending, {load_rows(HOLDOUT).__len__()} holdout.")


if __name__ == "__main__":
    main()
