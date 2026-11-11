"""Tests for tools/cashapp_statements.py — no PDFs, no network, standard library only.

The parser was written against real Cash App statements, so these tests pin the
three things that actually went wrong while building it: a wrapped description
being attached to the wrong row, a page footer being absorbed as text, and a
payment funded by a linked bank being counted as a Cash App outflow.
"""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import cashapp_statements as cs  # noqa: E402  (path set up above)

STATEMENT = """\
Balance on Jan 1           Change this month            Balance on Jan 31

$0.00                       $0.00                          $0.00

Money In                                                        + $300.00

Money Out                                                        - $324.89

Transactions

Date     Description                               Details                            Fee     Amount

Jan 2    Google                                    Cash App Pay                  $0.00      $24.89

Jan 3    To Sample Person from Capital One Bank     Cash App payment              $0.00      $40.00
         x0001

Jan 4    From U.S. Bank x0002                      Standard transfer             $0.00    + $300.00

Jan 5    Cash App                                  Overdraft coverage repayment  $0.00     $260.00

Jan 6    Tmobile Postpaid Pda                      Cash App Card                 $0.00      $40.00

                                                                             3/6
\fJanuary 2026
                                              Account Statement
"""


class TestSplitMoney(unittest.TestCase):
    def test_outflow_is_negative(self):
        fee, amount, description = cs.split_money(
            "Tmobile Postpaid Pda      Cash App Card      $0.00      $81.65"
        )
        self.assertEqual(amount, Decimal("-81.65"))
        self.assertEqual(fee, Decimal("0.00"))
        self.assertIn("Tmobile", description)

    def test_inflow_is_positive(self):
        _, amount, _ = cs.split_money(
            "From U.S. Bank x0002     Standard transfer     $0.00    + $196.39"
        )
        self.assertEqual(amount, Decimal("196.39"))

    def test_thousands_separator(self):
        _, amount, _ = cs.split_money("H E B      Cash App Card      $0.00    $1,122.24")
        self.assertEqual(amount, Decimal("-1122.24"))

    def test_needs_two_money_columns(self):
        self.assertIsNone(cs.split_money("only a description $24.89"))


class TestParseStatement(unittest.TestCase):
    def setUp(self):
        with mock.patch.object(cs, "pdf_to_text", return_value=STATEMENT):
            self.rows, self.declared_in, self.declared_out = cs.parse_statement("x.pdf")

    def test_row_count(self):
        self.assertEqual(len(self.rows), 5)

    def test_declared_totals_are_read(self):
        self.assertEqual(self.declared_in, Decimal("300.00"))
        self.assertEqual(self.declared_out, Decimal("324.89"))

    def test_wrapped_description_belongs_to_the_row_above(self):
        person = next(r for r in self.rows if "Sample Person" in r.description)
        self.assertIn("x0001", person.description)
        self.assertEqual(person.amount, Decimal("-40.00"))

    def test_page_footer_is_not_absorbed(self):
        tmobile = next(r for r in self.rows if "Tmobile" in r.description)
        self.assertNotIn("3/6", tmobile.description)
        self.assertNotIn("Account Statement", tmobile.description)


class TestCategorize(unittest.TestCase):
    def row(self, description, amount):
        row = cs.Row("Jan", "1", description, Decimal("0.00"), Decimal(amount), "x.pdf")
        row.bank_funded = bool(cs.BANK_FUNDED_RE.search(description))
        row.category = cs.categorize(row)
        return row

    def test_bank_funded_payment(self):
        self.assertEqual(
            self.row("To Sample Partner from U.S. Bank x0002 | Cash App payment", "-300").category,
            "bank_funded_payment",
        )

    def test_bank_funded_without_account_suffix(self):
        # June 2026: the trailing "x0001" is absent from the row entirely.
        self.assertEqual(
            self.row("To Sample Person from Capital One Bank | Cash App payment", "-175").category,
            "bank_funded_payment",
        )

    def test_plain_payment_is_not_bank_funded(self):
        self.assertEqual(
            self.row("To Sample Partner | Cash App payment", "-17").category, "payment_out"
        )

    def test_borrow_repayment(self):
        self.assertEqual(
            self.row("Cash App | Overdraft coverage repayment", "-91.32").category,
            "borrow_repayment",
        )

    def test_card_purchase(self):
        self.assertEqual(
            self.row("H E B Austin TX | Cash App Card", "-40.68").category, "card_purchase"
        )

    def test_payroll(self):
        self.assertEqual(
            self.row("AMAZON.COM SVCS PAYROLL | Direct deposit", "63.61").category, "payroll_in"
        )


class TestBalanceAffecting(unittest.TestCase):
    def test_bank_funded_outflow_is_excluded(self):
        rows = [
            cs.Row("Jan", "1", "To X from U.S. Bank x0002", Decimal("0"),
                   Decimal("-300"), "f", bank_funded=True),
            cs.Row("Jan", "2", "H E B | Cash App Card", Decimal("0"), Decimal("-40"), "f"),
            cs.Row("Jan", "3", "From U.S. Bank x0002", Decimal("0"),
                   Decimal("300"), "f", bank_funded=True),
        ]
        kept = cs.balance_affecting(rows)
        self.assertEqual(len(kept), 2)
        in_total, out_total = cs.totals(kept)
        self.assertEqual(in_total, Decimal("300"))
        self.assertEqual(out_total, Decimal("40"))

    def test_bank_funded_inflow_is_kept(self):
        # Money genuinely arriving must never be dropped: it moved the balance.
        rows = [cs.Row("Jan", "1", "From U.S. Bank x0002", Decimal("0"),
                       Decimal("300"), "f", bank_funded=True)]
        self.assertEqual(len(cs.balance_affecting(rows)), 1)


if __name__ == "__main__":
    unittest.main()
