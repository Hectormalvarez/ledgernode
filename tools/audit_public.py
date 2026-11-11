#!/usr/bin/env python3
"""Fail if personal detail has leaked into a tracked file.

The household's real names, institutions, balances and figures live in `.household.env`, which is
git-ignored. Tracked files carry roles instead: `Bank A`, `Employer B`, `Partner`, `${VARIABLE}`.

This script is the check, not a fixer. It exits non-zero when a tracked file contains something that
should only exist locally, so the rule survives without anyone having to remember it.

Two rule sets, because the parsers are a special case:

  STRICT  docs, tasks, README — no institutions, no people, no cent-precise amounts, no host detail.
  CODE    tools, tests, infra — institutions are allowed. `cashapp_statements.py` matches the literal
          phrase "Cash App Card" because that is what the real statement prints; renaming it would
          break the tool against the very data it exists to parse. Everything else still applies.

Usage:  python3 tools/audit_public.py [-v]
Exit:   0 clean, 1 violations found, 2 could not run
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Institutions and employers: only forbidden in STRICT files.
BRANDS = [
    "Capital One", "U.S. Bank", "US Bank", "Cash App", "Walgreens", "Amazon", "Fidelity",
    "Portfolio Recovery", "Caine & Weiner", "Caine", "Affirm", "Klarna", "Afterpay",
    "Buckman", "SchoolCafe", "T-Mobile", "TMobile", "Spectrum", "Randalls", "H-E-B",
    "Wal-Mart", "Walmart", "Whole Foods", "Sams Scan", "SAMS SCAN", "Empire Jewelry",
    "Discover Bank",
]

# Real people and their accounts: forbidden everywhere.
NAMES = ["Vanessa", "Hailey", "Hector", "Virginia", "Alvarez", "Jenny", "Ernesto", "Fritzy",
         "Benjamin"]

# Paths that may carry institution names, because the code matches those strings literally.
CODE_PREFIXES = ("tools/", "tests/", "infra/")

# Files that are allowed an exception, with the reason.
EXEMPT = {
    "LICENSE": "copyright holder is intentional and required",
    "tools/audit_public.py": "contains the pattern list itself",
}

CHECKS = [
    # Cent-precise amounts are only a leak in prose. The parsers and their fixtures must contain
    # cents — that is the thing under test — so this check is limited to STRICT paths.
    ("cent-precise amount", re.compile(r"\$\d[\d,]*\.\d{2}"), "strict"),
    ("private LAN address", re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "all"),
    ("host or login name", re.compile(r"\busrv-\d+\b|\bhadev\b"), "all"),
    ("real card tail", re.compile(r"\bx(?!000[0-9])\d{4}\b", re.IGNORECASE), "all"),
]

ALLOWED_IPS = {"192.168.1.10", "192.168.1.11", "192.168.1.12"}
ALLOWED_CARD_TAILS = {"x0000", "x0001", "x0002"}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [p for p in out.split("\x00") if p]


def is_strict(path: str) -> bool:
    return not path.startswith(CODE_PREFIXES)


def scan(path: str, text: str) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    strict = is_strict(path)
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, pattern, scope in CHECKS:
            if scope == "strict" and not strict:
                continue
            for m in pattern.finditer(line):
                token = m.group(0)
                low = token.lower()
                if label == "private LAN address" and token in ALLOWED_IPS:
                    continue
                if label == "real card tail" and low in ALLOWED_CARD_TAILS:
                    continue
                hits.append((lineno, label, token))
        for brand in BRANDS:
            if strict and brand.lower() in line.lower():
                hits.append((lineno, "institution name", brand))
        for name in NAMES:
            if name.lower() in line.lower():
                hits.append((lineno, "person name", name))
    return hits


def main() -> int:
    verbose = "-v" in sys.argv
    files = tracked_files()

    if ".household.env" in files:
        print("VIOLATION: .household.env is tracked; it must stay git-ignored")
        return 1

    total = 0
    for rel in files:
        if rel in EXEMPT:
            if verbose:
                print(f"  exempt  {rel}  ({EXEMPT[rel]})")
            continue
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        hits = scan(rel, text)
        if hits:
            total += len(hits)
            print(f"\n{rel}")
            for lineno, label, token in hits:
                print(f"  {lineno:>5}  {label:<20} {token!r}")

    print()
    if total:
        print(f"FAIL — {total} violation(s) across {len(files)} tracked files")
        print("Move the value to .household.env and reference it by role or ${VARIABLE}.")
        return 1
    print(f"PASS — {len(files)} tracked files, no personal detail found")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError:
        print("could not list tracked files; run inside the git repository", file=sys.stderr)
        sys.exit(2)
