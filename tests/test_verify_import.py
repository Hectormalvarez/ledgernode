"""Tests for tools/verify_import.py — no network, no ledger, standard library only."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import verify_import as vi  # noqa: E402  (path set up above)

HEADER = (
    "Account Number,Transaction Description,Transaction Date,"
    "Transaction Type,Transaction Amount,Balance\n"
)


def write_csv(rows: list[str], header: str = HEADER) -> str:
    """Write a temporary CSV and return its path."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    handle.write(header)
    handle.write("".join(rows))
    handle.close()
    return handle.name


def exit_code(func, *args, **kwargs) -> int:
    """Run a callable that is expected to exit, returning its code."""
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        try:
            func(*args, **kwargs)
        except SystemExit as exc:
            return int(exc.code)
    raise AssertionError("expected the call to exit")


class QuantityTests(unittest.TestCase):
    def test_rounds_twelve_decimal_places(self):
        self.assertEqual(str(vi.quantity("603.950000000000")), "603.95")

    def test_pads_single_decimal(self):
        self.assertEqual(str(vi.quantity("556.2")), "556.20")


class LoadFileTests(unittest.TestCase):
    def test_returns_rows_and_newest_balance(self):
        path = write_csv(
            [
                "7718,Coffee,01/15/25,Debit,10.00,90.00\n",
                "7718,Refund,01/16/25,Credit,5.00,95.00\n",
            ]
        )
        rows, balance = vi.load_file(path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("2025-01-15", "withdrawal", vi.quantity("10"), "Coffee"))
        self.assertEqual(rows[1], ("2025-01-16", "deposit", vi.quantity("5"), "Refund"))
        self.assertEqual(str(balance), "95.00")

    def test_negative_debit_is_a_deposit(self):
        """The bank labels its POS reversal as Debit with a negative amount."""
        path = write_csv(["7718,POS Reversal,01/15/25,Debit,-10.00,100.00\n"])
        rows, _ = vi.load_file(path)
        self.assertEqual(rows[0][1], "deposit")
        self.assertEqual(str(rows[0][2]), "10.00")

    def test_bad_date_exits_2(self):
        path = write_csv(["7718,Coffee,2025-01-15,Debit,10.00,90.00\n"])
        self.assertEqual(exit_code(vi.load_file, path), vi.EXIT_ERROR)

    def test_bad_amount_exits_2(self):
        path = write_csv(["7718,Coffee,01/15/25,Debit,abc,90.00\n"])
        self.assertEqual(exit_code(vi.load_file, path), vi.EXIT_ERROR)

    def test_empty_balance_exits_2(self):
        path = write_csv(["7718,Coffee,01/15/25,Debit,10.00,\n"])
        self.assertEqual(exit_code(vi.load_file, path), vi.EXIT_ERROR)

    def test_missing_column_exits_2(self):
        path = write_csv(["7718,Coffee,01/15/25,Debit,10.00\n"], header="Description,Amount\n")
        self.assertEqual(exit_code(vi.load_file, path), vi.EXIT_ERROR)

    def test_header_only_exits_2(self):
        path = write_csv([])
        self.assertEqual(exit_code(vi.load_file, path), vi.EXIT_ERROR)


class RowsFromGroupTests(unittest.TestCase):
    def group(self, kind: str) -> dict:
        return {
            "attributes": {
                "transactions": [
                    {
                        "type": kind,
                        "amount": "-10.000000000000",
                        "date": "2025-01-15T00:00:00+00:00",
                        "description": "Coffee",
                    }
                ]
            }
        }

    def test_withdrawal_is_kept(self):
        rows = vi.rows_from_group(self.group("withdrawal"))
        self.assertEqual(rows, [("2025-01-15", "withdrawal", vi.quantity("10"), "Coffee")])

    def test_opening_balance_is_ignored(self):
        self.assertEqual(vi.rows_from_group(self.group("opening balance")), [])

    def test_group_without_splits_is_ignored(self):
        self.assertEqual(vi.rows_from_group({"attributes": {}}), [])

    def transfer_group(self, source_id: str, destination_id: str) -> dict:
        return {
            "attributes": {
                "transactions": [
                    {
                        "type": "transfer",
                        "amount": "40.000000000000",
                        "date": "2025-01-20T00:00:00+00:00",
                        "description": "CASH APP",
                        "source_id": source_id,
                        "destination_id": destination_id,
                    }
                ]
            }
        }

    def test_transfer_out_of_the_account_reads_as_withdrawal(self):
        # Reclassified bank rows must still compare against the bank's own export.
        rows = vi.rows_from_group(self.transfer_group("1", "32"), account_id=1)
        self.assertEqual(rows, [("2025-01-20", "withdrawal", vi.quantity("40"), "CASH APP")])

    def test_transfer_into_the_account_reads_as_deposit(self):
        rows = vi.rows_from_group(self.transfer_group("32", "1"), account_id=1)
        self.assertEqual(rows, [("2025-01-20", "deposit", vi.quantity("40"), "CASH APP")])

    def test_transfer_between_other_accounts_is_ignored(self):
        self.assertEqual(vi.rows_from_group(self.transfer_group("32", "33"), account_id=1), [])

    def test_transfer_without_account_context_is_ignored(self):
        self.assertEqual(vi.rows_from_group(self.transfer_group("1", "32")), [])


class CompareTests(unittest.TestCase):
    def rows(self, *triples):
        return [(d, k, vi.quantity(a), s) for d, k, a, s in triples]

    def run_compare(self, file_rows, ledger_rows) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return vi.compare(file_rows, ledger_rows)

    def test_identical_ledgers_are_clean(self):
        rows = self.rows(("2025-01-15", "withdrawal", "10.00", "Coffee"))
        self.assertEqual(self.run_compare(rows, list(rows)), vi.EXIT_CLEAN)

    def test_duplicate_rows_must_be_counted_not_collapsed(self):
        """Two identical rows on one day are legitimate; both must be present."""
        row = self.rows(("2025-01-15", "withdrawal", "10.00", "Coffee"))[0]
        self.assertEqual(self.run_compare([row, row], [row, row]), vi.EXIT_CLEAN)
        self.assertEqual(self.run_compare([row, row], [row]), vi.EXIT_MISMATCH)

    def test_missing_row_is_a_mismatch(self):
        present = self.rows(("2025-01-15", "withdrawal", "10.00", "Coffee"))
        file_rows = self.rows(
            ("2025-01-15", "withdrawal", "10.00", "Coffee"),
            ("2025-01-16", "deposit", "5.00", "Refund"),
        )
        self.assertEqual(self.run_compare(file_rows, present), vi.EXIT_MISMATCH)

    def test_extra_row_is_a_mismatch(self):
        file_rows = self.rows(("2025-01-15", "withdrawal", "10.00", "Coffee"))
        ledger_rows = self.rows(
            ("2025-01-15", "withdrawal", "10.00", "Coffee"),
            ("2025-01-16", "deposit", "5.00", "Refund"),
        )
        self.assertEqual(self.run_compare(file_rows, ledger_rows), vi.EXIT_MISMATCH)


class PaginationTests(unittest.TestCase):
    def test_short_read_exits_2(self):
        """If the API returns fewer groups than it claims, refuse to compare."""
        page = {
            "data": [
                {
                    "attributes": {
                        "transactions": [
                            {
                                "type": "withdrawal",
                                "amount": "-1.00",
                                "date": "2025-01-15T00:00:00+00:00",
                                "description": "x",
                            }
                        ]
                    }
                }
            ],
            "meta": {"pagination": {"total": 5, "total_pages": 1}},
        }
        original = vi.api_get
        vi.api_get = lambda url, token: page  # type: ignore[assignment]
        try:
            code = exit_code(vi.fetch_ledger, "http://example", "t", 1, "2025-01-01", "2025-01-31")
        finally:
            vi.api_get = original  # type: ignore[assignment]
        self.assertEqual(code, vi.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()

