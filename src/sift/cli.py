#!/usr/bin/env python3
"""Sift - Junk Line Filter (Inference Only)."""

import argparse
import hashlib
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

from .model import JunkFilter, is_likely_junk
from .strings_extract import extract_strings_from_path

UNCERTAIN_MARGIN = 0.15
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "sift.pkl"


def load_model(model_path):
    if not model_path.exists():
        return None
    try:
        with model_path.open("rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def looks_binary(path):
    """Return True if a file looks like a binary (contains null bytes)."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except:
        return False


def run_strings(path):
    """Extract printable strings from a file.

    Prefer the native `strings` binary when available, but fall back to the
    bundled pure-Python extractor so the installed CLI works on Windows too.
    """
    if shutil.which("strings"):
        try:
            result = subprocess.run(
                ["strings", path],
                capture_output=True, text=True, errors="replace"
            )
            return result.stdout.splitlines()
        except SystemExit:
            raise
        except Exception as e:
            sys.stderr.write(f"sift: external strings failed, falling back to Python extractor: {e}\n")
    try:
        return extract_strings_from_path(Path(path))
    except OSError as e:
        sys.stderr.write(f"sift: strings extraction failed: {e}\n")
        sys.exit(1)


def classify_lines(lines, flt, threshold):
    kept, junk, unambiguous_keep, unambiguous_junk = [], [], [], []
    uncertain = []

    for line in lines:
        line = line.rstrip("\n\r")
        if is_likely_junk(line):
            junk.append(line)
            unambiguous_junk.append(line)
            continue
        prob_junk = flt.predict_proba([line])[0][1]
        if prob_junk >= threshold:
            junk.append(line)
            unambiguous_junk.append(line)
        elif abs(prob_junk - threshold) < UNCERTAIN_MARGIN or (0.3 < prob_junk < 0.7):
            uncertain.append(line)
        else:
            kept.append(line)
            unambiguous_keep.append(line)

    total_classified = len(kept) + len(junk) + len(uncertain)
    unambig_rate = len(uncertain) / total_classified if total_classified > 0 else 0.0
    return kept, junk, uncertain, unambiguous_keep, unambiguous_junk, unambig_rate


def write_lines(lines, out=sys.stdout.buffer):
    """Write lines to buffer, handling broken pipe cleanly."""
    try:
        for l in lines:
            out.write((l + "\n").encode("utf-8", errors="replace"))
    except BrokenPipeError:
        pass


def main():
    p = argparse.ArgumentParser(
        description="Sift - Junk Line Filter",
        usage="%(prog)s [options] [files or '-' (stdin)]"
    )
    p.add_argument("files", nargs="*", help="Input text files (or - for stdin)")
    p.add_argument("--show-labels", action="store_true", help="Show [KEEP/JUNK prob] prefix per line")
    p.add_argument("--show-junk", action="store_true", help="Show junk lines only")
    p.add_argument("--show-unambiguous", action="store_true", help="Show unambiguous lines only")
    p.add_argument("--no-strings", action="store_true",
                   help="Read input files as text instead of running 'strings' first")
    p.add_argument("--threshold", type=float, default=0.5, help="Junk threshold (default: 0.5)")
    p.add_argument(
        "--model",
        help="Path to model file (default: bundled model packaged with sift)",
    )
    args = p.parse_args()

    # Load model
    model_path = Path(args.model).expanduser().resolve() if args.model else DEFAULT_MODEL_PATH
    flt = JunkFilter(threshold=args.threshold)
    model = load_model(model_path)
    if model:
        model.threshold = args.threshold
        flt = model
    else:
        sys.stderr.write(
            f"sift: model not found at {model_path}. "
            "Retrain it with `python scripts/train_eval.py`.\n"
        )
        return 1

    # Collect lines
    if args.files:
        lines = []
        for fpath in args.files:
            file_path = Path(fpath)
            if not args.no_strings:
                lines.extend(run_strings(str(file_path)))
            else:
                with file_path.open("rb") as f:
                    raw = f.read()
                    if b"\x00" in raw[:8192]:
                        sys.stderr.write(
                            f"sift: {file_path} looks like a binary. "
                            f"Remove --no-strings or pipe strings output:\n"
                            f"  strings {fpath} | {sys.argv[0]} [options]\n"
                        )
                        continue
                with file_path.open("r", encoding="utf-8", errors="replace") as f:
                    lines.extend(f.readlines())
    elif sys.stdin.isatty():
        p.print_help()
        return 0
    else:
        import io
        stdin_binary = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
        lines = stdin_binary.readlines()

    if not lines:
        return

    # Dedupe
    seen = set()
    unique = []
    for l in lines:
        h = hashlib.md5(l.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(l)
    lines = unique

    kept, junk, uncertain, unambiguous_keep, unambiguous_junk, unambig_rate = \
        classify_lines(lines, flt, args.threshold)

    if args.show_labels:
        try:
            for line in lines:
                line = line.rstrip("\n\r")
                if is_likely_junk(line):
                    print(f"[JUNK  100%] {line}")
                    continue
                prob = flt.predict_proba([line])[0][1]
                tag = "JUNK" if prob >= args.threshold else "KEEP"
                print(f"[{tag} {prob:>5.0%}] {line}")
        except BrokenPipeError:
            pass
    elif args.show_junk:
        write_lines(junk)
    elif args.show_unambiguous:
        write_lines(unambiguous_keep)
        write_lines(unambiguous_junk)
    else:
        write_lines(kept)

    total = len(kept) + len(junk) + len(uncertain)
    print(f"Sift: kept={len(kept)} junk={len(junk)} uncertain={len(uncertain)} ({unambig_rate:.1%} ambiguous) total={total}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
