"""Shared library for sift - JunkFilter and utilities."""

import math
import re
from collections import Counter
from difflib import SequenceMatcher

import numpy as np


KNOWN_PREFIXES = (
    "__",
    ".text",
    ".data",
    ".rodata",
    "glibc",
    "api-ms-",
    "kernel32",
    "user32",
    "msvcrt",
    "libstdc++",
    "utf-",
    "rsds",
)
FORMAT_PATTERN_RE = re.compile(r"%[-+ #0-9.*hljztL]*[A-Za-z]")
HEX_PATTERN_RE = re.compile(r"0x[0-9a-fA-F]+")
VOWELS = set("aeiou")


def shannon_entropy(s):
    if not s:
        return 0.0
    counts = Counter(s)
    total = len(s)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def bigram_entropy(s):
    if len(s) < 2:
        return 0.0
    bigrams = [s[i:i + 2] for i in range(len(s) - 1)]
    counts = Counter(bigrams)
    total = len(bigrams)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def max_char_repeat(line):
    if not line:
        return 0.0
    best = 1
    current = 1
    for idx in range(1, len(line)):
        if line[idx] == line[idx - 1]:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return float(best)


def repeated_substring_score(line):
    if len(line) < 4:
        return 0.0
    best = 0.0
    length = len(line)
    for width in range(2, min(6, (length // 2) + 1)):
        counts = Counter(line[i:i + width] for i in range(length - width + 1))
        repeated = sum(width * count for token, count in counts.items() if count > 1 and token.strip())
        best = max(best, repeated / length)
    return best


def vowel_consonant_ratio(line):
    letters = [c.lower() for c in line if c.isalpha()]
    if not letters:
        return 0.0
    vowels = sum(1 for c in letters if c in VOWELS)
    consonants = sum(1 for c in letters if c not in VOWELS)
    if consonants == 0:
        return float(vowels)
    return vowels / consonants


def similarity_to_nearest(text, candidates):
    if not text or not candidates:
        return 0.0
    lowered = text.lower()
    best = 0.0
    target_len = len(lowered)
    for candidate in candidates:
        if abs(len(candidate) - target_len) > max(4, target_len):
            continue
        score = SequenceMatcher(None, lowered, candidate).ratio()
        if score > best:
            best = score
    return best


def extract_features(line, keep_tokens=None):
    line = str(line)
    length = len(line)
    if length == 0:
        return [0.0] * 21
    alpha = sum(1 for c in line if c.isalpha()) / length
    digit = sum(1 for c in line if c.isdigit()) / length
    punct = sum(1 for c in line if not c.isalnum() and not c.isspace()) / length
    space = sum(1 for c in line if c.isspace()) / length
    upper = sum(1 for c in line if c.isupper()) / length
    ascii_ratio = sum(1 for c in line if ord(c) < 128) / length
    printable_ratio = sum(1 for c in line if c.isprintable()) / length
    has_null_bytes = 1.0 if "\x00" in line else 0.0
    symbol_ratio = sum(1 for c in line if not c.isalnum() and not c.isspace()) / length
    contains_known_prefix = 1.0 if any(prefix in line.lower() for prefix in KNOWN_PREFIXES) else 0.0
    contains_format_pattern = 1.0 if FORMAT_PATTERN_RE.search(line) else 0.0
    contains_path_like = 1.0 if any(token in line for token in ("/", "\\", ":")) else 0.0
    contains_hex_pattern = 1.0 if HEX_PATTERN_RE.search(line) else 0.0
    return [
        float(length),
        shannon_entropy(line),
        alpha,
        digit,
        punct,
        space,
        upper,
        0.0,
        ascii_ratio,
        printable_ratio,
        has_null_bytes,
        symbol_ratio,
        max_char_repeat(line),
        repeated_substring_score(line),
        contains_known_prefix,
        contains_format_pattern,
        contains_path_like,
        contains_hex_pattern,
        bigram_entropy(line),
        1.0 - similarity_to_nearest(line, keep_tokens),
        vowel_consonant_ratio(line),
    ]


def is_likely_junk(line):
    line = str(line).strip()
    l = len(line)
    if l == 0:
        return False
    if l <= 4:
        pc = sum(1 for c in line if not c.isalnum() and not c.isspace())
        if pc / l >= 0.8:
            return True
    e = shannon_entropy(line)
    if l <= 8 and e >= 4.0:
        ai = sum(1 for c in line if c.isalnum())
        if ai / l <= 0.3:
            return True
    pc = sum(1 for c in line if not c.isalnum() and not c.isspace())
    if pc / l >= 0.9 and l >= 3:
        return True
    return False


class JunkFilter:
    """Junk line classifier using char n-grams + features."""

    def __init__(self, threshold=0.95):
        self.threshold = threshold
        self._is_fitted = False
        self.keep_tokens = []

    def _build_keep_tokens(self, X_text, y):
        keep = sorted({str(text).lower() for text, label in zip(X_text, y) if label == 0 and text})
        keep = [token for token in keep if 2 <= len(token) <= 64]
        self.keep_tokens = keep[:2000]

    def _build_matrix(self, X_text, fit_vectorizer=False):
        from scipy import sparse

        texts = [str(text) for text in X_text]
        if fit_vectorizer:
            X_vec = self.vectorizer.fit_transform(texts)
        else:
            X_vec = self.vectorizer.transform(texts)
        X_feat = np.array([extract_features(text, self.keep_tokens) for text in texts], dtype=np.float64)
        return sparse.hstack([X_vec, sparse.csr_matrix(X_feat)], format="csr")

    def fit(self, X_text, y):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.utils.class_weight import compute_class_weight

        self._build_keep_tokens(X_text, y)
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5),
            max_features=5000, norm="l2", sublinear_tf=True
        )
        X = self._build_matrix(X_text, fit_vectorizer=True)

        classes = np.array([0, 1])
        cw = compute_class_weight('balanced', classes=classes, y=y)
        class_weight = {0: cw[0], 1: cw[1]}

        self.classifier = LogisticRegression(
            C=1.0, class_weight=class_weight,
            max_iter=1000, solver='lbfgs', random_state=42
        )
        self.classifier.fit(X, y)
        self._is_fitted = True
        return self

    def partial_fit(self, X_text, y):
        if not self._is_fitted:
            return self.fit(X_text, y)
        return self.fit(X_text, y)

    def predict_proba(self, X_text):
        if not self._is_fitted:
            return np.array([[0.5, 0.5]] * len(X_text))
        X = self._build_matrix(X_text, fit_vectorizer=False)
        return self.classifier.predict_proba(X)

    def predict(self, X_text):
        probs = self.predict_proba(X_text)
        return [1 if p[1] >= self.threshold else 0 for p in probs]
