# ADR-0005 — One model for three statements: Bank A, prepaid app, Bank B

| | |
|---|---|
| **Status** | Accepted, 2026-11-10 |
| **Tasks** | T-27 (extraction schema), T-28 (Bank B parser), T-29 (cross-source match), T-30 (import) |
| **Story** | [US-004](../stories/US-004-budget-and-debt-visibility.md) |
| **Validated against** | Firefly III 6.7.9; Bank A 2,268-row export; prepaid app statements Jan–Oct 2026 |

## Context

Household money moves through three institutions, and the ledger currently sees one of them. The
prepaid app statements make the problem concrete: of 692 rows, 131 are payments funded by **Bank B
x0002** ($7,250) that the ledger has never seen, and many others describe money that already appears
in the Bank A export from the other side.

The naive fix — import everything from every statement — is wrong by roughly $22,000. Bank A's
2026 export alone contains **164 `PREPAID APP` debits totalling $22,000**. Those and prepaid app's own
rows are the same money seen twice.

## Decision

### 1. Every institution is an asset account; the account is the unit of truth

`Bank A` (exists), `prepaid app`, `Bank B` become three asset accounts in Firefly. A statement
is authoritative for what happened **inside** that institution. Nothing else is.

### 2. Money crossing between our own accounts is a transfer, recorded once

A movement between two of the three is a transfer, never two expenses. The side recorded is the one
from the institution the money physically left, because that institution's statement is the one whose
balance is being asserted.

Proved example: `PREPAID APP PREPAID APP 8009691940 −$940` in the Bank A export and
`Loan repayment (#DB9Q5XXY0) $940` in the prepaid app statement are one event. It is booked once,
from Bank A.

### 3. Matching is exact on amount and loose on date, and the offset is measured

Pairs are matched on the **same amount to the cent**, opposite direction, within a date window.
Measured on Jan–Oct 2026: **24 of 24** Bank A→prepaid app transfers matched, every one at exactly
**−1 day** (prepaid app posts a day before Bank A). prepaid app had **zero** unmatched inflows on the
Bank A side. The window defaults to 0…−4 days and the tool always reports the offsets it saw,
so a change in posting behaviour is visible rather than silent.

### 4. The losing side is retained as evidence, not imported

A matched prepaid app row is not deleted or dropped; it is marked `duplicate_of` the ledger row it
corresponds to. It remains available as proof that the transfer completed, and as the thing that
detects a missing row: an unmatched statement row is a real finding, not noise.

### 5. Every row is exactly one of four kinds

| Kind | Meaning | Booked as |
|---|---|---|
| `transfer_internal` | between two of our own accounts | one transfer, from the losing/winning side per §2 |
| `income` | payroll, refunds, transfers from outside | revenue |
| `expense` | purchases, bills, payments to third parties | expense |
| `duplicate_of` | the other side of a transfer already booked | nothing — retained as evidence |

A row that cannot be classified is **an error, not a default**. Guessing a kind is how a ledger
becomes fiction.

### 6. Every account must reconcile to its own printed closing balance

Each of the three statements prints opening and closing balance. After import:
`opening + inflows − outflows = closing`, per account, per statement. This is the same discipline as
`verify_import.py` and it is the only reason to trust any of it. A failure is a defect, never a
rounding note.

### 7. The duplicate-count guard runs before any write

Before writing, assert that for every matched pair **exactly one** side is in the import set. If both
or neither are present, abort without writing. This is the single check that prevents the $22,000
mistake, and it is cheap.

## Identifiers: cards are not accounts

The statements name **cards**, not accounts. Confirmed with the owner on 2026-11-10:

| Where it appears | Identifier | Resolves to |
|---|---|---|
| prepaid app: `From/To … Bank A x0001` | Bank A debit card | **Bank A** — the account already in the ledger |
| prepaid app: `From/To … Bank B x0002` | Bank B debit card | **Bank B** — one new asset account |

So exactly **one** new asset account is required, not two, and every `PREPAID APP` debit in the Capital
One export is already correctly attributed. No row is ever booked to a card; a card is a funding
instrument belonging to an account. The Bank B account number behind card x0002 is to be read from
its statements when they arrive, and recorded here.

### The same card can carry two labels, and moving money to it costs a fee

Card ending **0001** appears in the prepaid app as both `Bank A x0001` (the issuing bank) and
`<network> Bank x0001` (the card network). Reading the second as a separate institution was wrong: it
is the household's own debit card, viewed through a different label. Any future card whose network and
issuer differ will present the same trap. Match on the **last four digits and the amounts**, never on
the institution name in the descriptor.

Transfers from prepaid app to that card are charged at **1.75%, rising to 1.95% from 2026** — the January
2026 statement announces the change in its first line. Twelve transfers cost **$75**, and the fee
is invisible unless the amount sent is compared with the amount that arrived: `$750` sent lands as
`$740`. Booking both the prepaid app row and the Bank A row as income/expense double-counts
roughly **$4,000 of spending and $1,800 of income**; the correct treatment is one transfer plus the
fee as its own expense.

## Consequences

- Three statements become one ledger with no double counting, each account independently reconciled.
- Bank B moves from invisible to fully accounted — the largest single win here.
- prepaid app stops being an opaque "PREPAID APP" line and becomes merchants.
- **Cost:** the 171 own-account `PREPAID APP PREPAID APP 8009691940` debits in the Bank A export must be
  reclassified from expense to transfer into the prepaid app account. That is an edit of existing rows,
  and it must ship in the same operation as the prepaid app import, or net worth is wrong by $22,000
  in the wrong direction.
- The 121 unmatched Bank A `PREPAID APP` debits are **not** defects: they are payments made with the
  Bank A debit card through prepaid app's payment rail, which never enter the prepaid app balance and
  therefore never appear on its statement. They stay as expenses and need no counterpart.
