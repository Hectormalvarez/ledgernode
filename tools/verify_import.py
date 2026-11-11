#!/usr/bin/env python3
"""Verify a Capital One statement export against the Firefly III ledger.

Read-only. Compares a statement file with the ledger for one account and reports
any row-level discrepancy:

    - rows in the file versus rows in the ledger
    - the multiset of (date, type, amount, description)
    - the net change per date
    - the ledger balance against the balance on the newest row of the file

Exit codes: 0 clean, 1 mismatch, 2 error (nothing was changed in either case).
Constraints and their evidence: docs/decisions/0002-importer-constraints.md
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime
import decimal
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import NoReturn

DEFAULT_ENV_FILE = "/srv/ledgernode/.importer.env"
DEFAULT_URL = os.environ.get("FIREFLY_III_URL", "http://127.0.0.1:8090").rstrip("/")
PAGE_SIZE = 100

EXIT_CLEAN = 0
EXIT_MISMATCH = 1
EXIT_ERROR = 2


def fail(message: str) -> NoReturn:
    """Report an error and leave with the error exit code."""
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_ERROR)


def load_token(env_file: str) -> str:
    """Return the access token from the environment, else from the env file.

    The token is never taken from the command line: arguments leak into shell
    history and process listings.
    """
    token = os.environ.get("FIREFLY_III_ACCESS_TOKEN", "").strip()
    if token:
        return token
    try:
        with open(env_file, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("FIREFLY_III_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except OSError as exc:
        fail(f"cannot read token from {env_file}: {exc}")
    fail(f"no FIREFLY_III_ACCESS_TOKEN in the environment or in {env_file}")


def api_get(url: str, token: str) -> dict:
    """GET a JSON document, converting transport failures into exit code 2."""
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        fail(f"HTTP {exc.code} from {url}: {exc.read()[:200].decode('utf-8', 'replace')}")
    except (urllib.error.URLError, TimeoutError) as exc:
        fail(f"cannot reach {url}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"response from {url} was not JSON: {exc}")


def fetch_ledger(base_url: str, token: str, account_id: int, start: str, end: str) -> list[tuple]:
    """Return every ledger row for the account within the date range.

    Pagination is asserted: if the number of rows collected disagrees with the
    total the API itself reports, this aborts rather than comparing a partial
    ledger. A dropped page would otherwise look like missing transactions.
    """
    rows: list[tuple] = []
    expected_total = None
    groups_seen = 0
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"limit": PAGE_SIZE, "page": page, "start": start, "end": end}
        )
        url = f"{base_url}/api/v1/accounts/{account_id}/transactions?{query}"
        payload = api_get(url, token)
        groups = payload.get("data", [])
        pagination = payload.get("meta", {}).get("pagination", {})
        if expected_total is None:
            expected_total = pagination.get("total")
        for group in groups:
            groups_seen += 1
            rows.extend(rows_from_group(group, account_id))
        total_pages = pagination.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    # `total` counts transaction groups, including types this check ignores
    # (an opening balance, for example), so it is compared against the number of
    # groups read — never against the filtered row count.
    if expected_total is not None and groups_seen != expected_total:
        fail(
            f"the ledger returned {groups_seen} transaction groups but claims "
            f"{expected_total}; refusing to compare a partial ledger"
        )
    return rows


def quantity(value) -> decimal.Decimal:
    """Normalise an amount to two decimals.

    The ledger stores numeric(32,12), so values read back as 603.950000000000.
    """
    return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"))


def rows_from_group(group: dict, account_id: int | None = None) -> list[tuple]:
    """Reduce one transaction group to a comparable row.

    Returns nothing for anything that is not money moving in or out of the account
    under test, so opening balances and unrelated transfers do not register as
    discrepancies.

    A transfer counts as a withdrawal when the account under test is the source and
    a deposit when it is the destination. Without this, reclassifying a bank's
    "CASH APP" debits from expenses to transfers would make every one of them look
    like a missing row even though the balance is still correct.
    """
    attributes = group.get("attributes", {})
    splits = attributes.get("transactions") or []
    if not splits:
        return []
    first = splits[0]
    kind = first.get("type", "")
    if kind == "transfer":
        source = str(first.get("source_id", ""))
        destination = str(first.get("destination_id", ""))
        if account_id is not None and source == str(account_id):
            kind = "withdrawal"
        elif account_id is not None and destination == str(account_id):
            kind = "deposit"
        else:
            return []
    if kind not in ("withdrawal", "deposit"):
        return []
    date = str(first.get("date", ""))[:10]
    amount = abs(quantity(first.get("amount", 0)))
    description = first.get("description", "") or ""
    return [(date, kind, amount, description)]


def load_file(path: str) -> tuple[list[tuple], decimal.Decimal]:
    """Read the statement export once, returning rows and the newest balance.

    Direction comes from the signed amount, not the type column alone: the bank
    labels its -10 POS reversal as Debit, which means money coming in.

    Malformed values exit with code 2 and a line number, never a traceback: an
    unexpected crash must not be mistaken for a mismatch by a caller.
    """
    required = {
        "Transaction Date",
        "Transaction Type",
        "Transaction Amount",
        "Transaction Description",
        "Balance",
    }
    rows: list[tuple] = []
    newest_day: datetime.date | None = None
    newest_balance = decimal.Decimal("0")
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            absent = required - set(reader.fieldnames or [])
            if absent:
                fail(f"{path} is missing column(s): {', '.join(sorted(absent))}")
            for line_number, raw in enumerate(reader, start=2):
                try:
                    day = datetime.datetime.strptime(raw["Transaction Date"], "%m/%d/%y").date()
                except (ValueError, TypeError):
                    fail(
                        f"{path} line {line_number}: unparseable date "
                        f"{raw['Transaction Date']!r}; expected m/d/y"
                    )
                try:
                    amount = decimal.Decimal((raw["Transaction Amount"] or "").strip())
                    balance = decimal.Decimal((raw["Balance"] or "").strip())
                except (decimal.InvalidOperation, AttributeError):
                    fail(
                        f"{path} line {line_number}: amount {raw['Transaction Amount']!r} or "
                        f"balance {raw['Balance']!r} is not a number"
                    )
                if (raw["Transaction Type"] or "").strip() == "Credit":
                    signed = amount
                else:
                    signed = -amount
                kind = "deposit" if signed > 0 else "withdrawal"
                rows.append(
                    (
                        day.isoformat(),
                        kind,
                        abs(quantity(amount)),
                        raw["Transaction Description"] or "",
                    )
                )
                if newest_day is None or day >= newest_day:
                    newest_day = day
                    newest_balance = quantity(balance)
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    if not rows:
        fail(f"{path} contains no transactions")
    return rows, newest_balance


def compare(file_rows: list[tuple], ledger_rows: list[tuple]) -> int:
    """Print the comparison and return the exit code."""
    file_counter = collections.Counter(file_rows)
    ledger_counter = collections.Counter(ledger_rows)
    missing = file_counter - ledger_counter
    extra = ledger_counter - file_counter

    sign = {"withdrawal": -1, "deposit": 1}
    file_net: dict[str, decimal.Decimal] = collections.defaultdict(decimal.Decimal)
    ledger_net: dict[str, decimal.Decimal] = collections.defaultdict(decimal.Decimal)
    for date, kind, amount, _ in file_rows:
        file_net[date] += amount * sign[kind]
    for date, kind, amount, _ in ledger_rows:
        ledger_net[date] += amount * sign[kind]
    differing = [day for day in sorted(file_net) if quantity(file_net[day]) != quantity(
        ledger_net.get(day, decimal.Decimal(0)))]

    print(f"file      : {len(file_rows)} rows")
    print(f"ledger    : {len(ledger_rows)} rows in the same date range")
    print(f"missing   : {sum(missing.values())} row(s) in the file but not the ledger")
    print(f"extra     : {sum(extra.values())} row(s) in the ledger but not the file")
    print(f"days      : {len(file_net)} dates compared, {len(differing)} differ")

    for date, kind, amount, description in sorted(missing.elements())[:20]:
        print(f"  MISSING {date} {kind:<10} {amount:>9} {description[:55]}")
    for date, kind, amount, description in sorted(extra.elements())[:20]:
        print(f"  EXTRA   {date} {kind:<10} {amount:>9} {description[:55]}")
    for day in differing[:20]:
        print(f"  DAY     {day} file {quantity(file_net[day])} "
              f"vs ledger {quantity(ledger_net.get(day, decimal.Decimal(0)))}")

    if missing or extra or differing:
        print("result    : MISMATCH")
        return EXIT_MISMATCH
    print("result    : clean")
    return EXIT_CLEAN


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a statement file against the ledger.")
    parser.add_argument("--file", required=True, help="path to the Capital One CSV export")
    parser.add_argument("--account-id", type=int, default=1, help="Firefly asset account id")
    parser.add_argument("--url", default=DEFAULT_URL, help="Firefly III base URL")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="file holding the API token")
    args = parser.parse_args()

    token = load_token(args.env_file)
    file_rows, expected = load_file(args.file)
    days = sorted({row[0] for row in file_rows})
    first_day = datetime.date.fromisoformat(days[0])
    last_day = datetime.date.fromisoformat(days[-1])
    # Widen the query by a few days: if a statement is missing its first or last
    # row, the file's own range shrinks, and a query bounded by that range would
    # hide the ledger row that proves it.
    ledger_rows = fetch_ledger(
        args.url,
        token,
        args.account_id,
        (first_day - datetime.timedelta(days=3)).isoformat(),
        (last_day + datetime.timedelta(days=3)).isoformat(),
    )
    in_range = [row for row in ledger_rows if days[0] <= row[0] <= days[-1]]
    outside = len(ledger_rows) - len(in_range)
    exit_code = compare(file_rows, in_range)
    if outside:
        print(
            f"note      : {outside} ledger row(s) fall outside {days[0]}..{days[-1]} "
            "and were not compared"
        )

    account = api_get(f"{args.url}/api/v1/accounts/{args.account_id}", token)
    actual = quantity(account.get("data", {}).get("attributes", {}).get("current_balance", 0))
    net = sum(
        (amount * (1 if kind == "deposit" else -1) for _, kind, amount, _ in file_rows),
        decimal.Decimal(0),
    )
    print(
        f"balance   : file {expected} | ledger {actual} | "
        f"implied opening {quantity(expected - net)}"
    )
    if exit_code == EXIT_CLEAN and expected != actual:
        print("result    : MISMATCH (balance differs)")
        print(
            "          rows inside the date range matched, so look at its edges: "
            "a missing first or last row shifts the balance without changing the rows"
        )
        return EXIT_MISMATCH
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - a crash must never look like a mismatch
        print(f"error: unexpected failure: {exc!r}", file=sys.stderr)
        sys.exit(EXIT_ERROR)


