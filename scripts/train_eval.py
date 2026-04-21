#!/usr/bin/env python3
"""Retrain and evaluate on holdout."""
import argparse
import csv
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sift.model import JunkFilter

parser = argparse.ArgumentParser()
parser.add_argument("--holdout", default="datasets/labeled/holdout_adversarial.csv")
parser.add_argument("--labels", default="datasets/labeled/labels.csv")
parser.add_argument("--model", default="src/sift/models/sift.pkl")
args = parser.parse_args()

# Train
rows = []
with (ROOT / args.labels).open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) >= 2:
            text = ",".join(row[:-1])
            label = row[-1].strip()
            if label in ("0", "1"):
                rows.append((text, int(label)))
texts, y = zip(*rows)
flt = JunkFilter(threshold=0.5)
flt.fit(list(texts), list(y))
model_path = ROOT / args.model
model_path.parent.mkdir(parents=True, exist_ok=True)
with model_path.open("wb") as f:
    pickle.dump(flt, f)
print(f"Trained on {len(rows)} rows")

# Eval on holdout
tp = tn = fp = fn = 0
misclassified = []
with (ROOT / args.holdout).open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 2:
            continue
        true = row[-1].strip()
        if true not in ("0", "1"):
            continue
        true = int(true)
        text = ",".join(row[:-1])
        prob = flt.predict_proba([text])[0][1]
        pred = 1 if prob >= 0.5 else 0
        if pred == 1 and true == 1:
            tp += 1
        elif pred == 0 and true == 0:
            tn += 1
        elif pred == 1 and true == 0:
            fp += 1
            misclassified.append((text, prob, true, pred))
        else:
            fn += 1
            misclassified.append((text, prob, true, pred))

total = tp + tn + fp + fn
acc = (tp + tn) / total if total else 0
prec = tp / (tp + fp) if (tp + fp) else 0
rec = tp / (tp + fn) if (tp + fn) else 0

print(f"Holdout total: {total}")
print(f"Accuracy: {acc:.1%}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")
if misclassified:
    print(f"Misclassified ({len(misclassified)}):")
    for text, prob, true, pred in misclassified:
        true_str = "KEEP" if true == 0 else "JUNK"
        pred_str = "KEEP" if pred == 0 else "JUNK"
        print(f"  [{pred_str} {prob:.0%}] {text[:60]}")
else:
    print("No misclassifications.")
