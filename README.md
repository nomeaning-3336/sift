# sift

`sift` filters likely junk strings out of text or `strings` output using a small character n-gram classifier plus handcrafted structure features.

## Install

```bash
git clone https://github.com/nomeaning-3336/sift.git
cd sift
python -m pip install -e .
```

After that, `sift` is available as a command:

```bash
sift --help
```

The install works on both Windows and Linux. On Linux, `sift` will use the system
`strings` binary when available; on Windows, or when `strings` is missing, it
falls back to a bundled pure-Python extractor automatically.

## Common usage

Show model labels and scores:

```bash
sift --show-labels --no-strings input.txt
```

Default behavior runs `strings` first for file inputs:

```bash
sift sample.exe
```

## Before / after

Raw `strings` output from a binary often mixes useful symbols with opcode-like junk:

```text
__gmon_start__
D$8H
RSDS
AUATUWVSH
UTF-8
t9eHA
libc.so.6
```

Running `sift sample.exe` keeps the structured strings and drops the junk:

```text
__gmon_start__
RSDS
UTF-8
libc.so.6
```

If you want to inspect borderline cases in a text file, use labels:

```text
$ cat input.txt
RSDS
R@DS
D$8H
LANG
t9eHA
```

```bash
sift --show-labels --no-strings input.txt
```

```text
[KEEP   12%] RSDS
[JUNK   71%] R@DS
[JUNK  100%] D$8H
[KEEP   10%] LANG
[JUNK   83%] t9eHA
```

## Project layout

- `src/sift/`: installable CLI and model code
- `src/sift/models/`: packaged trained model
- `scripts/`: training, evaluation, and dataset maintenance utilities
- `datasets/`: labeled training and holdout CSVs
- `tools/`: standalone helper utilities such as `pystrings.py`

## Training utilities

Retrain and evaluate the packaged model:

```bash
python scripts/train_eval.py
```

Generate an adversarial holdout:

```bash
python scripts/adv_holdout.py
```

Append only new mistakes from the adversarial holdout:

```bash
python scripts/fix_misclass.py
```
