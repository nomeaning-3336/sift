#!/usr/bin/env python3
"""Eval model on pending labels, show misclassifications."""
import csv
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

model_path = ROOT / "src" / "sift" / "models" / "sift.pkl"
pending_path = ROOT / "datasets" / "labeled" / "pending_labels.csv"

with model_path.open("rb") as f:
    flt = pickle.load(f)

pending = []
with pending_path.open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) >= 2:
            text = ",".join(row[:-1])
            label = row[-1].strip()
            pending.append((text, label))

print(f"Pending: {len(pending)} rows")

# Eval
correct = misclassified = uncertain = 0
junk_correct = junk_total = keep_correct = keep_total = 0
misclass_list = []

for text, model_pred_str in pending:
    prob = flt.predict_proba([text])[0][1]
    pred = 1 if prob >= 0.5 else 0
    model_pred = "JUNK" if pred == 1 else "KEEP"

    # uncertain band
    if abs(prob - 0.5) < 0.15 or (0.3 < prob < 0.7):
        uncertain += 1
        continue

    # correct?
    if (pred == 1 and model_pred_str == "JUNK") or (pred == 0 and model_pred_str == "KEEP"):
        correct += 1
    else:
        misclassified += 1
        misclass_list.append((text, model_pred_str, model_pred, prob))

print(f"Correct: {correct}, Misclassified: {misclassified}, Uncertain: {uncertain}")
denominator = correct + misclassified
accuracy = correct / denominator if denominator else 0.0
print(f"Accuracy (certain only): {accuracy:.1%}")
print(f"\nMisclassified ({len(misclass_list)}):")
for text, model_pred, sift_pred, prob in sorted(misclass_list, key=lambda x: -x[3]):
    print(f"  model={sift_pred} {prob:.0%}  actual={model_pred}  {text[:70]}")
