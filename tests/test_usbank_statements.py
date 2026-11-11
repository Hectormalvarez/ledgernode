"""Tests for tools/usbank_statements.py — no PDFs, no network, standard library only.

Pins the two things that would silently corrupt a U.S. Bank import: the Holds and
Releases section being counted as real spending, and the sign of a refund being
lost inside a section that is otherwise all withdrawals.
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import usbank_statements as us  # noqa: E402  (path set up above)

STATEMENT = """\
Monthly Statement

 Card ID:                    4995506609

 Beginning Balance:          $12.18

 Ending Balance:             $7.74

Credits

 Date         Reference                                         Amount

 10/31/26     Funds Transfer with Validation                    $124.34

 02/02/26     Funds Transfer with Validation                    $157.34

Purchases and Withdrawals

 Date       Reference                        Amount

 10/30/26   Purchase                          -$9.16

 10/29/26   Returned Item                     $5.00

Fees

It looks like there are no fees for the month selected.
\fHolds and Releases

 Date       Reference               Amount

 10/01/26   POS Pre-Authorization   -$17.00

 10/02/26   POS Pre-Authorization   $14.75

Totals for Statement for Period Ending February 2026

Credits                                                     $2,108.01

Purchases and Withdrawals                                   -$2,138.94
"""


class TestParse(unittest.TestCase):
    def setUp(self):
        self.rows, self.holds, self.declared = us.parse_statement_text(STATEMENT, "s.pdf")

    def test_only_settled_sections_become_rows(self):
        self.assertEqual(len(self.rows), 4)

    def test_holds_are_counted_and_discarded(self):
        self.assertEqual(self.holds, 2)
        self.assertFalse(any("Pre-Authorization" in r.description for r in self.rows))

    def test_credit_is_positive(self):
        row = next(r for r in self.rows if r.amount == Decimal("124.34"))
        self.assertEqual(row.section, "credits")

    def test_purchase_with_minus_is_negative(self):
        row = next(r for r in self.rows if r.amount == Decimal("-9.16"))
        self.assertEqual(row.section, "purchases")

    def test_refund_without_minus_stays_positive(self):
        # A minus sign is what made it a withdrawal; its absence means money back.
        row = next(r for r in self.rows if "Returned" in r.description)
        self.assertEqual(row.amount, Decimal("5.00"))

    def test_period_comes_from_the_row_date(self):
        self.assertEqual({r.period for r in self.rows}, {"2026-10", "2026-02"})

    def test_declared_totals_are_read_as_magnitudes(self):
        self.assertEqual(self.declared["2026-02"], (Decimal("2108.01"), Decimal("2138.94")))


class TestTotals(unittest.TestCase):
    def test_totals_separate_directions(self):
        rows = [
            us.Row("01", "02", "26", "in", "credits", Decimal("100.00"), "f"),
            us.Row("01", "03", "26", "out", "purchases", Decimal("-40.00"), "f"),
        ]
        credits, purchases = us.totals(rows)
        self.assertEqual(credits, Decimal("100.00"))
        self.assertEqual(purchases, Decimal("40.00"))


class TestPdfGuard(unittest.TestCase):
    def test_missing_pdftotext_exits_with_message(self):
        with mock.patch.object(us.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(SystemExit) as caught:
                us.pdf_to_text("x.pdf")
        self.assertIn("pdftotext", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
