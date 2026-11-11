#!/usr/bin/env python3
"""Extract U.S. Bank card statements (PDF) into one verified CSV.

Why this exists
---------------
U.S. Bank card x0002 funds a large share of the household's spending and is the
only one of the three institutions the ledger could never see. Cash App's
statements name it 131 times, for $7,250, with no counterpart anywhere.

Layout notes, learned from the real file rather than assumed
-----------------------------------------------------------
The statement is a flat text table in four sections, and only some of them are
settled money:

    Credits                    money in          " 10/31/26  Funds Transfer  $124.34"
    Purchases and Withdrawals  money out         " 10/30/26  Purchase        -$9.16"
    Fees                       usually empty
    Holds and Releases         POS pre-auths, NOT settled money

The Holds section is the trap. It prints pre-authorisations that later settle as
real purchases, so counting both double-counts the same money. It is parsed and
deliberately discarded, and the count is reported so the exclusion is visible.

Sign convention: credits are positive, purchases carry an explicit minus. A
purchase row *without* a minus is a refund and stays positive. Verified against
the statement's own "Totals for Statement" block, which matches to the cent.

Usage
-----
    python3 tools/usbank_statements.py --file ~/Desktop/202601-10.pdf
    python3 tools/usbank_statements.py --file ... --csv usbank.csv --verbose

Exit codes: 0 = every declared total reconciled, 1 = one did not, 2 = nothing parsed.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal

SECTIONS = {
    "Credits": "credits",
    "Purchases and Withdrawals": "purchases",
    "Fees": "fees",
    "Holds and Releases": "holds",
}
SETTLED = {"credits", "purchases"}

ROW_RE = re.compile(
    r"^\s*(\d{2})/(\d{2})/(\d{2})\s+(.+?)\s+(-?)\$([\d,]*\.\d{2})\s*$"
)
PERIOD_RE = re.compile(r"Totals for Statement for Period Ending (\w+) (\d{4})")
DECL_CREDITS_RE = re.compile(r"^Credits\s+\$([\d,]*\.\d{2})\s*$", re.MULTILINE)
DECL_PURCHASES_RE = re.compile(
    r"^Purchases and Withdrawals\s+-?\$([\d,]*\.\d{2})\s*$", re.MULTILINE
)
MONTHS = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
}


@dataclass
class Row:
    month: str
    day: str
    year: str
    description: str
    section: str
    amount: Decimal  # signed: positive = money in
    source: str

    @property
    def period(self) -> str:
        return f"20{self.year}-{self.month}"


def pdf_to_text(path: str) -> str:
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", path, "-"],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise SystemExit("pdftotext not found. Install poppler-utils.") from exc
    return proc.stdout


def parse_statement_text(
    text: str, source: str = ""
) -> tuple[list[Row], int, dict[str, tuple[Decimal, Decimal]]]:
    """Parse laid-out statement text into settled rows plus declared totals.

    Returns (rows, holds_skipped, declared) where declared maps a period
    ("2026-02") to the credits/purchases totals the statement prints for it.
    """
    rows: list[Row] = []
    holds_skipped = 0
    section = "header"

    for line in text.splitlines():
        stripped = line.strip()
        if stripped in SECTIONS:
            section = SECTIONS[stripped]
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        mm, dd, yy, description, sign, amount = match.groups()
        if section not in SETTLED:
            # Holds and Releases are pre-authorisations that settle later as real
            # purchases. Counting them would double-count the same money.
            holds_skipped += 1
            continue
        value = Decimal(amount.replace(",", ""))
        if section == "purchases":
            value = -value if sign else value  # no minus in this section = refund
        rows.append(
            Row(
                month=mm, day=dd, year=yy,
                description=re.sub(r"\s{2,}", " ", description).strip(),
                section=section, amount=value, source=source,
            )
        )

    declared: dict[str, tuple[Decimal, Decimal]] = {}
    for period_match in PERIOD_RE.finditer(text):
        name, year = period_match.group(1), period_match.group(2)
        month = MONTHS.get(name)
        if not month:
            continue
        tail = text[period_match.end():]
        credits_hit = DECL_CREDITS_RE.search(tail)
        purchases_hit = DECL_PURCHASES_RE.search(tail)
        if not (credits_hit and purchases_hit):
            continue
        declared[f"{year}-{month}"] = (
            Decimal(credits_hit.group(1).replace(",", "")),
            Decimal(purchases_hit.group(1).replace(",", "")),  # magnitude
        )
    return rows, holds_skipped, declared


def totals(rows: list[Row]) -> tuple[Decimal, Decimal]:
    return (
        sum((r.amount for r in rows if r.amount > 0), Decimal("0.00")),
        sum((-r.amount for r in rows if r.amount < 0), Decimal("0.00")),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract U.S. Bank statement PDFs to CSV.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="a single statement PDF")
    group.add_argument("--dir", help="directory of statement PDFs")
    parser.add_argument("--csv", help="write the extracted rows here")
    parser.add_argument("--verbose", action="store_true", help="print every row")
    args = parser.parse_args(argv)

    if args.file:
        if not os.path.isfile(args.file):
            print(f"not a file: {args.file}", file=sys.stderr)
            return 2
        paths = [args.file]
    else:
        if not os.path.isdir(args.dir):
            print(f"not a directory: {args.dir}", file=sys.stderr)
            return 2
        paths = sorted(
            os.path.join(args.dir, f)
            for f in os.listdir(args.dir)
            if f.lower().endswith(".pdf")
        )
    if not paths:
        print("no PDFs found", file=sys.stderr)
        return 2

    all_rows: list[Row] = []
    declared_all: dict[str, tuple[Decimal, Decimal]] = {}
    holds = 0
    for path in paths:
        rows, holds_skipped, declared = parse_statement_text(
            pdf_to_text(path), os.path.basename(path)
        )
        all_rows.extend(rows)
        holds += holds_skipped
        declared_all.update(declared)

    if not all_rows:
        print("nothing parsed — is this a U.S. Bank statement?", file=sys.stderr)
        return 2

    by_period: dict[str, list[Row]] = {}
    for row in all_rows:
        by_period.setdefault(row.period, []).append(row)

    print(f"{'period':<10}{'rows':>6}{'credits':>13}{'purchases':>13}"
          f"{'net':>12}  check")
    print("-" * 74)
    failures = 0
    for period in sorted(by_period):
        rows = by_period[period]
        credits, purchases = totals(rows)
        check = "no declared total"
        if period in declared_all:
            want_credits, want_purchases = declared_all[period]
            ok = credits == want_credits and purchases == want_purchases
            failures += 0 if ok else 1
            check = "reconciled" if ok else (
                f"MISMATCH c{want_credits:,.2f} p{want_purchases:,.2f}"
            )
        print(f"{period:<10}{len(rows):>6}{credits:>13,.2f}{purchases:>13,.2f}"
              f"{credits - purchases:>12,.2f}  {check}")

    all_rows.sort(key=lambda r: (r.year, r.month, r.day))
    if args.verbose:
        for row in all_rows:
            print(f"  {row.month}/{row.day}/{row.year} {row.amount:>11,.2f}  "
                  f"{row.description}", file=sys.stderr)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["period", "day", "description", "section", "amount", "source"])
            for row in all_rows:
                writer.writerow([row.period, row.day, row.description, row.section,
                                 f"{row.amount:.2f}", row.source])
        print(f"\nwrote {len(all_rows)} rows to {args.csv}")

    credits, purchases = totals(all_rows)
    print(f"\n{len(all_rows)} settled rows across {len(by_period)} period(s)")
    print(f"credits {credits:,.2f}   purchases {purchases:,.2f}")
    print(f"excluded {holds} POS pre-authorisation row(s) from Holds and Releases")
    if failures:
        print(f"FAILED: {failures} period(s) did not match the declared total", file=sys.stderr)
        return 1
    if not declared_all:
        print("no declared totals present: nothing could be reconciled", file=sys.stderr)
        return 1
    print("every period with a declared total reconciled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
