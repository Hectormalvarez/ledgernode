# US-002 — Trust every import without re-deriving it by hand

| | |
|---|---|
| **ID** | US-002 |
| **Status** | Partially delivered — AC1, 2, 4, 5, 6 verified; AC3 (repair) pending T-13 |
| **Date** | 2026-11-09 |
| **Owner** | Product Owner |
| **Epic** | Household finance visibility (v1) |
| **Depends on** | US-001 (T-07 closed); repair gated on T-13 |

## Description

**As** the household owner
**I want** one check after each monthly import that compares the ledger to the bank's file
**So that** I can trust the monthly report without re-deriving it by hand

## Context & Scope

The first two imports of a correct 2,268-row file both produced a wrong ledger, and neither failure was
visible in the UI. In one case every credit was rejected; in the other, 22 rows disappeared as
"duplicates" with no message at all. Both were found by comparing the ledger to the file by hand —
work that will not be repeated reliably every month. This story makes that comparison a single command.

The constraints this tool must respect are recorded in
[ADR-0002](../decisions/0002-importer-constraints.md).

### In scope

- A read-only check comparing a statement file against the ledger for one account.
- Reporting: rows in file versus rows in ledger, every date whose net differs, and the specific missing
  and extra rows by date, amount, description and type.
- Comparing the resulting balance with the balance on the file's last row.
- An explicit, separately invoked repair that adds only the missing rows, once each.

### Out of scope

- Automating the import itself, scheduling, notifications, or any web interface.
- Support for other banks, other file formats, or more than one account.
- Correcting rows that are present but wrong; those are reported, never rewritten.
- Deleting "extra" rows automatically.

## Acceptance Criteria

1. Given a statement file, when the check runs, then it reports the row count in the file and in the
   ledger, and names every date whose net differs.
2. Given a mismatch, then the specific missing and extra rows are listed with date, amount,
   description and type — not merely a total.
3. Given the mismatch is duplicates that were dropped on import, when repair is explicitly requested,
   then those rows are added exactly once and re-checking passes.
4. Given a clean ledger, then the check reports the resulting balance and compares it with the balance
   on the file's last row.
5. *(error path)* Given the ledger is unreachable, the token is invalid, or the ledger returns fewer
   rows than its own pagination claims, then the check reports that plainly, changes nothing, and
   signals failure distinctly from a mismatch.
6. The check never writes unless repair is explicitly requested, and running repair twice adds nothing
   the second time.

## Success measure

The next monthly import is verified with one command, and any row-level discrepancy is identified by
date and amount without opening a database client.

## Open questions

1. **Account name normalisation.** Descriptions are compared verbatim today. If Firefly rules later
   rewrite descriptions, the comparison must compare post-rule text or ignore descriptions — to be
   decided when rules exist (T-09).
2. **Statement overlap.** Monthly files overlap at the boundary; whether the check should expect the
   overlap to be ignored or reported is unresolved until the second real import happens.

## Technical Guidance

Not defined here. Verified tool behaviour and the constraints for the implementation are in
[ADR-0002](../decisions/0002-importer-constraints.md). Delivery is gated: read-only verification may
ship, repair waits for the restore rehearsal (T-13).
