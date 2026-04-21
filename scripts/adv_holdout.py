import random
import string
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sift.model import JunkFilter

MODEL_PATH = ROOT / "src" / "sift" / "models" / "sift.pkl"
OUTPUT = ROOT / "datasets" / "labeled" / "holdout_adversarial.csv"

TARGET_LOW = 0.40
TARGET_HIGH = 0.60
TARGET_COUNT = 200

# ---------------------------
# Mutation strategies
# ---------------------------

def mutate(s):
    ops = [
        insert_random,
        delete_random,
        flip_case,
        duplicate_chunks,
        inject_symbols,
        mix_with_junk_pattern,
    ]
    return random.choice(ops)(s)


def insert_random(s):
    i = random.randint(0, len(s))
    c = random.choice(string.printable)
    return s[:i] + c + s[i:]


def delete_random(s):
    if not s:
        return s
    i = random.randint(0, len(s)-1)
    return s[:i] + s[i+1:]


def flip_case(s):
    return "".join(
        c.upper() if random.random() < 0.5 else c.lower()
        for c in s
    )


def duplicate_chunks(s):
    if len(s) < 2:
        return s
    i = random.randint(0, len(s)//2)
    j = random.randint(i+1, len(s))
    chunk = s[i:j]
    return s[:j] + chunk + s[j:]


def inject_symbols(s):
    symbols = "$@#%^&*()_+=|\\<>~"
    i = random.randint(0, len(s))
    return s[:i] + random.choice(symbols) + s[i:]


def mix_with_junk_pattern(s):
    junk = random.choice([
        "D$8H",
        "T$PH",
        "|$0H",
        "A_A^A\\",
        "UVWH",
        "AUATUWVSH",
    ])
    return s + junk if random.random() < 0.5 else junk + s


# ---------------------------
# Load seed data
# ---------------------------

def load_labels(path):
    import csv
    data = []
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if len(row) >= 2:
                text = ",".join(row[:-1])
                label = int(row[-1])
                data.append((text, label))
    return data


# ---------------------------
# Main
# ---------------------------

def main():
    with MODEL_PATH.open("rb") as f:
        model: JunkFilter = pickle.load(f)

    data = load_labels(ROOT / "datasets" / "labeled" / "labels.csv")

    results = set()

    print("[*] Generating adversarial samples...")

    while len(results) < TARGET_COUNT:
        base, label = random.choice(data)

        mutated = base
        for _ in range(random.randint(1, 4)):
            mutated = mutate(mutated)

        prob = model.predict_proba([mutated])[0][1]

        if TARGET_LOW <= prob <= TARGET_HIGH:
            pred = 1 if prob >= 0.5 else 0

            # Flip label to create challenge
            adv_label = label

            results.add((mutated, adv_label, prob, pred))

            print(f"[{len(results)}] {prob:.2f} :: {mutated}")

    print(f"\n[*] Writing {len(results)} samples → {OUTPUT}")

    import csv
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["line", "label"])
        for text, label, _, _ in results:
            w.writerow([text, label])


if __name__ == "__main__":
    main()
